#!/usr/bin/env python3
"""
IPVanish Widget Daemon
Polls /proc/net/dev + /run/ipvanish-active-conf every second.
Writes /run/user/1000/ipvanish-widget.json and exposes D-Bus service.
"""

import json
import os
import re
import signal
import sys
import time
import urllib.request
from collections import deque
from pathlib import Path
from typing import Optional

# ── constants ──────────────────────────────────────────────────────────────
PROC_NET_DEV     = Path('/proc/net/dev')
ACTIVE_CONF_FILE = Path('/run/ipvanish-active-conf')
UID              = os.getuid()
JSON_OUT         = Path(f'/run/user/{UID}/ipvanish-widget.json')
HISTORY_LEN      = 20
IP_REFRESH_SECS  = 30
TICK_INTERVAL    = 1.0
DBUS_SERVICE     = 'com.ditherz.IPVanishWidget'
DBUS_PATH        = '/com/ditherz/IPVanishWidget'
DBUS_IFACE       = 'com.ditherz.IPVanishWidget'


# ── pure helpers (importable for tests) ────────────────────────────────────

def _parse_tun0(content: str) -> Optional[tuple[int, int]]:
    """Return (rx_bytes, tx_bytes) for tun0 from /proc/net/dev content, or None."""
    for line in content.splitlines():
        if 'tun0' in line:
            parts = line.split()
            try:
                return int(parts[1]), int(parts[9])
            except (IndexError, ValueError):
                return None
    return None


def _parse_ovpn_location(path: Optional[str]) -> tuple[str, str]:
    """
    Parse 'ipvanish-CC-City-Name-code-XX.ovpn' -> ('City Name, CC', 'code-XX.ipvanish.com').
    Returns ('Not connected', '') if path is None or unparseable.
    """
    if not path:
        return ('Not connected', '')
    stem = Path(path).stem  # e.g. 'ipvanish-SG-Singapore-sin-a02'
    m = re.match(r'^ipvanish-([A-Z]{2})-(.+)-([a-z]{2,4}-[a-z]\d+)$', stem)
    if not m:
        return ('Unknown', '')
    cc       = m.group(1)
    city_raw = m.group(2)   # 'Singapore' or 'Los-Angeles'
    code     = m.group(3)   # 'sin-a02'
    city     = city_raw.replace('-', ' ')
    return (f'{city}, {cc}', f'{code}.ipvanish.com')


def _normalise(history: list[float]) -> list[float]:
    """Scale history values to 0.0-1.0 relative to window max; floor at 0.01."""
    mx = max(history) if history else 0.0
    if mx == 0.0:
        return [0.01] * len(history)
    return [max(0.01, v / mx) for v in history]


def _fmt_bps(bps: float, *, bits: bool = False) -> str:
    """Format bytes/sec. bits=True multiplies by 8 and uses kb/Mb labels."""
    if bits:
        val = bps * 8
        if val >= 1_000_000:
            return f'{val / 1_000_000:.1f} Mb/s'
        if val >= 1_000:
            return f'{val / 1_000:.1f} kb/s'
        return f'{val:.0f} b/s'
    if bps >= 1_048_576:
        return f'{bps / 1_048_576:.1f} MB/s'
    if bps >= 1_024:
        return f'{bps / 1_024:.1f} KB/s'
    return f'{bps:.0f} B/s'


def _read_public_ip() -> str:
    """Fetch public IP from ipify; return empty string on failure."""
    try:
        with urllib.request.urlopen('https://api.ipify.org', timeout=5) as r:
            return r.read().decode().strip()
    except Exception:
        return ''


# ── D-Bus service ───────────────────────────────────────────────────────────
# Import dasbus at module level so annotations resolve correctly.
# If dasbus is missing, DBUS_AVAILABLE stays False and D-Bus is skipped.

DBUS_AVAILABLE = False
try:
    from dasbus.connection import SessionMessageBus
    from dasbus.server.interface import dbus_interface
    from dasbus.typing import Str
    DBUS_AVAILABLE = True
except ImportError:
    pass

if DBUS_AVAILABLE:
    @dbus_interface(DBUS_IFACE)
    class _IPVanishWidgetInterface:
        # _state_container is set before the service is registered
        _state_container: list = [{}]

        def GetStats(self) -> Str:
            return json.dumps(self._state_container[0])
else:
    _IPVanishWidgetInterface = None  # type: ignore[assignment,misc]


def _build_dbus_service(state_container: list) -> object:
    """Register D-Bus service. state_container[0] always has latest state."""
    if not DBUS_AVAILABLE or _IPVanishWidgetInterface is None:
        print('[daemon] D-Bus unavailable: dasbus not installed', file=sys.stderr)
        return None
    try:
        _IPVanishWidgetInterface._state_container = state_container
        bus = SessionMessageBus()
        svc = _IPVanishWidgetInterface()
        bus.publish_object(DBUS_PATH, svc)
        bus.register_service(DBUS_SERVICE)
        return svc
    except Exception as exc:
        print(f'[daemon] D-Bus registration failed: {exc}', file=sys.stderr)
        return None


# ── main loop ───────────────────────────────────────────────────────────────

class Daemon:
    def __init__(self) -> None:
        self._prev_net: Optional[tuple[int, int]] = None
        self._down_hist: deque[float] = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self._up_hist:   deque[float] = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self._public_ip: str = ''
        self._ip_last_checked: float = 0.0
        self._state: dict = {}
        self._state_container: list = [{}]
        self._running = True
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT,  self._stop)

    def _stop(self, *_) -> None:
        self._running = False

    def _tick_net(self) -> tuple[float, float]:
        try:
            content = PROC_NET_DEV.read_text()
        except OSError:
            return 0.0, 0.0
        current = _parse_tun0(content)
        if current is None:
            self._prev_net = None
            return 0.0, 0.0
        if self._prev_net is None:
            self._prev_net = current
            return 0.0, 0.0
        rx_now,  tx_now  = current
        rx_prev, tx_prev = self._prev_net
        self._prev_net = current
        down = max(0.0, float(rx_now - rx_prev))
        up   = max(0.0, float(tx_now - tx_prev))
        return down, up

    def _tick_ip(self) -> None:
        now = time.monotonic()
        if now - self._ip_last_checked >= IP_REFRESH_SECS or not self._public_ip:
            ip = _read_public_ip()
            if ip:
                self._public_ip = ip
            self._ip_last_checked = now

    def _tick_conf(self) -> tuple[str, str, bool]:
        try:
            conf_path = ACTIVE_CONF_FILE.read_text().strip()
            loc, host = _parse_ovpn_location(conf_path)
            connected = bool(conf_path)
        except OSError:
            loc, host, connected = 'Not connected', '', False
        return loc, host, connected

    def _write_json(self) -> None:
        try:
            JSON_OUT.write_text(json.dumps(self._state))
        except OSError as exc:
            print(f'[daemon] JSON write failed: {exc}', file=sys.stderr)

    def run(self) -> None:
        dbus_svc = _build_dbus_service(self._state_container)
        # Run GLib event loop in a background thread so D-Bus can handle calls
        if DBUS_AVAILABLE:
            import threading
            from gi.repository import GLib
            gloop = GLib.MainLoop()
            gthread = threading.Thread(target=gloop.run, daemon=True)
            gthread.start()
        print('[daemon] started', file=sys.stderr)
        while self._running:
            start = time.monotonic()

            down_bps, up_bps = self._tick_net()
            self._tick_ip()
            loc, host, connected = self._tick_conf()

            self._down_hist.append(down_bps)
            self._up_hist.append(up_bps)

            self._state = {
                'publicIP':       self._public_ip or '—',
                'serverLocation': loc,
                'serverHost':     host,
                'connected':      connected,
                'downBps':        down_bps,
                'upBps':          up_bps,
                'downHistory':    _normalise(list(self._down_hist)),
                'upHistory':      _normalise(list(self._up_hist)),
            }
            self._state_container[0] = self._state

            self._write_json()

            elapsed    = time.monotonic() - start
            sleep_time = max(0.0, TICK_INTERVAL - elapsed)
            time.sleep(sleep_time)

        print('[daemon] stopped', file=sys.stderr)


if __name__ == '__main__':
    Daemon().run()
