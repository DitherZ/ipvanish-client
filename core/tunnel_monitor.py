"""
core/tunnel_monitor.py
Monitors a VPN tunnel interface's upload/download speed via /proc/net/dev.
Emits speed_update(up_str, down_str) every second while active.
IPVanish-Client v2
"""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

DEV_FILE = "/proc/net/dev"


def _read_iface(name: str) -> tuple[int, int] | None:
    """Return (rx_bytes, tx_bytes) for `name`, or None if not present."""
    try:
        with open(DEV_FILE) as f:
            for line in f:
                if name in line:
                    parts = line.split()
                    # iface: rx_bytes rx_pkts ... tx_bytes tx_pkts ...
                    return int(parts[1]), int(parts[9])
    except (OSError, IndexError, ValueError):
        pass
    return None


def _fmt(bps: float) -> str:
    if bps >= 1_048_576:
        return f"{bps / 1_048_576:.1f} MB/s"
    if bps >= 1024:
        return f"{bps / 1024:.0f} KB/s"
    return f"{bps:.0f} B/s"


class TunnelMonitor(QObject):
    """
    Polls /proc/net/dev once per second for the active tunnel interface.
    Diffs consecutive readings to derive upload / download speed.
    Emits speed_update(upload_str, download_str) each tick.
    """
    speed_update = pyqtSignal(str, str)   # (up, down)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._iface: str = "tun0"
        self._last: tuple[int, int] | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def start(self, iface: str = "tun0") -> None:
        self._iface = iface
        self._last = _read_iface(self._iface)
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._last = None

    def _tick(self) -> None:
        current = _read_iface(self._iface)
        if current is None or self._last is None:
            self.speed_update.emit("—", "—")
            self._last = current
            return
        rx_now,  tx_now  = current
        rx_prev, tx_prev = self._last
        down = max(0, rx_now - rx_prev)
        up   = max(0, tx_now - tx_prev)
        self._last = current
        self.speed_update.emit(_fmt(up), _fmt(down))
