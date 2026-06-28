"""
core/backends/openvpn_backend.py
OpenVPN backend — generalised from the original connection.py logic.
IPVanish-Client v2
"""

from __future__ import annotations

import ipaddress
import os
import re
import subprocess
import time
from pathlib import Path
from typing import ClassVar

from core.backends.base import VPNBackend

IPVANISH_DNS = ["198.18.0.1", "198.18.0.2"]

# Subnets whose CDNs block VPN exit IPs — routed via real gateway instead of tunnel.
SPLIT_TUNNEL_NETS: list[str] = [
    "91.194.110.0/25",  # trafficdeposit.com video CDN (UA-Hosting SIA)
]
PID_FILE     = Path(__file__).parents[2] / "pid"
CONFIGS_DIR  = Path(__file__).parents[2] / "config"


def _default_gateway() -> str:
    """Read the current default gateway from the routing table."""
    try:
        out = subprocess.check_output(
            ["ip", "route", "show", "default"], text=True
        )
        for token in out.split():
            if token not in ("default", "via", "dev", "proto", "src", "metric"):
                try:
                    # First non-keyword after 'via' is the gateway IP
                    parts = out.split()
                    return parts[parts.index("via") + 1]
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass
    return "192.168.0.1"


def _cidr_to_ovpn(cidr: str) -> str:
    """Convert CIDR notation to 'IP NETMASK' for OpenVPN route directive."""
    net = ipaddress.IPv4Network(cidr, strict=False)
    return f"{net.network_address} {net.netmask}"


def _parse_dev(ovpn_path: Path) -> str:
    """Extract the tunnel interface name from a .ovpn file's dev directive."""
    try:
        for line in ovpn_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            # Match "dev tunX" or "dev tun" (no suffix → tun0 fallback)
            m = re.match(r"^dev\s+(tun\S*|tap\S*)", stripped, re.IGNORECASE)
            if m:
                iface = m.group(1)
                return iface if iface[-1].isdigit() else iface + "0"
    except OSError:
        pass
    return "tun0"


class OpenVPNBackend(VPNBackend):
    protocol: ClassVar[str] = "openvpn"

    def __init__(self) -> None:
        self._iface: str = "tun0"

    # ──── PUBLIC ──── #

    def connect(self, profile) -> None:  # type: ignore[override]
        from core.profiles import Profile as _Profile  # local import avoids circular dep
        assert isinstance(profile, _Profile)

        self._iface = _parse_dev(profile.path)
        ovpn_config = str(CONFIGS_DIR / "conn.ovpn")

        if profile.is_ipvanish and SPLIT_TUNNEL_NETS:
            with open(CONFIGS_DIR / "conn.ovpn", "a") as f:
                for net in SPLIT_TUNNEL_NETS:
                    f.write(f"\nroute {_cidr_to_ovpn(net)} net_gateway")

        # Single pkexec: disable IPv6 + launch openvpn in one polkit prompt
        script = (
            f"sysctl -q net.ipv6.conf.all.disable_ipv6=1 && "
            f"openvpn --config {ovpn_config} --daemon --writepid /tmp/ipvanish-ovpn.pid"
        )
        subprocess.run(
            ["pkexec", "bash", "-c", script],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for openvpn daemon to write its pid file (up to 5 s)
        pid_src = Path("/tmp/ipvanish-ovpn.pid")
        for _ in range(5):
            time.sleep(1)
            if pid_src.exists():
                PID_FILE.write_text(pid_src.read_text())
                break
        else:
            PID_FILE.write_text("0")

        # Poll for tunnel interface (up to 30 s — daemon mode needs more time)
        for _ in range(30):
            time.sleep(1)
            if self._iface in os.listdir("/sys/class/net"):
                break
        else:
            raise TimeoutError(
                f"{self._iface} interface did not appear within 30 seconds."
            )

        if profile.is_ipvanish:
            self._configure_dns_ipvanish()

    def disconnect(self) -> None:
        pid = 0
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
            except ValueError:
                pass
            PID_FILE.unlink(missing_ok=True)

        gw = _default_gateway()
        # Build one shell script: kill openvpn + restore IPv6 + restore DNS
        cmds = []
        if pid:
            cmds.append(f"kill -SIGTERM {pid} 2>/dev/null || true")
        cmds.append("sysctl -q net.ipv6.conf.all.disable_ipv6=0")
        for iface in os.listdir("/sys/class/net"):
            if iface == "lo":
                continue
            cmds.append(f"resolvectl default-route {iface} true 2>/dev/null || true")
            cmds.append(f"resolvectl dns {iface} {gw} 2>/dev/null || true")
        cmds.append(
            "cp /tmp/resolv.conf.ipvanish.bak /etc/resolv.conf 2>/dev/null || true"
        )

        subprocess.run(
            ["pkexec", "bash", "-c", " && ".join(cmds)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def is_connected(self) -> bool:
        return PID_FILE.exists() and self._iface in os.listdir("/sys/class/net")

    def interface_name(self) -> str | None:
        return self._iface if self.is_connected() else None

    # ──── PRIVATE ──── #

    def _configure_dns_ipvanish(self) -> None:
        # resolvectl only affects systemd-resolved consumers; /etc/resolv.conf users
        # (foreign mode) need the file rewritten directly.  Back it up first so
        # disconnect() can restore it.
        dns0, dns1 = IPVANISH_DNS
        cmds = [
            f"resolvectl dns {self._iface} {dns0} {dns1} 2>/dev/null || true",
            f"resolvectl default-route {self._iface} true 2>/dev/null || true",
            "cp /etc/resolv.conf /tmp/resolv.conf.ipvanish.bak",
            f"printf 'nameserver {dns0}\\nnameserver {dns1}\\n' > /etc/resolv.conf",
        ]
        subprocess.run(
            ["pkexec", "bash", "-c", " && ".join(cmds)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
