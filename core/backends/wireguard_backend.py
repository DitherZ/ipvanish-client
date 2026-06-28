"""
core/backends/wireguard_backend.py
WireGuard backend — wg-quick via pkexec (polkit).
Interface name derived from the config filename stem (capped at 15 chars per IFNAMSIZ).
IPVanish-Client v2
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import ClassVar

from core.backends.base import VPNBackend

IFNAMSIZ = 15  # Linux kernel interface name length limit (excluding NUL)


class WireGuardBackend(VPNBackend):
    protocol: ClassVar[str] = "wireguard"

    def __init__(self) -> None:
        self._iface: str | None = None
        self._conf_path: Path | None = None

    # ──── PUBLIC ──── #

    def connect(self, profile) -> None:  # type: ignore[override]
        self._iface = profile.path.stem[:IFNAMSIZ]
        self._conf_path = profile.path
        subprocess.run(
            ["pkexec", "wg-quick", "up", str(profile.path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def disconnect(self) -> None:
        if self._conf_path is None:
            return
        subprocess.run(
            ["pkexec", "wg-quick", "down", str(self._conf_path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._iface = None
        self._conf_path = None

    def is_connected(self) -> bool:
        if not self._iface:
            return False
        return self._iface in os.listdir("/sys/class/net")

    def interface_name(self) -> str | None:
        return self._iface if self.is_connected() else None
