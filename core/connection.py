"""
core/connection.py
VPN connection dispatcher — picks the correct backend by profile protocol
and runs it on a QThread. Public signals are unchanged from v1.
IPVanish-Client v2
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from core.backends import OpenVPNBackend, WireGuardBackend, VPNBackend
from core.profiles import Profile

_BACKENDS: dict[str, type[VPNBackend]] = {
    "openvpn":   OpenVPNBackend,
    "wireguard": WireGuardBackend,
}


# ──── WORKER ──── #

class ConnectionWorker(QObject):
    """Runs in a QThread — calls the blocking backend connect/disconnect."""
    connected     = pyqtSignal()
    disconnected  = pyqtSignal()
    error         = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, action: str, backend: VPNBackend, profile: Profile) -> None:
        super().__init__()
        self.action   = action
        self._backend = backend
        self._profile = profile

    def run(self) -> None:
        try:
            if self.action == "connect":
                self._do_connect()
            elif self.action == "disconnect":
                self._do_disconnect()
        except Exception as e:
            self.error.emit(str(e))

    def _do_connect(self) -> None:
        self.status_update.emit("Starting VPN…")
        self._backend.connect(self._profile)
        self.connected.emit()

    def _do_disconnect(self) -> None:
        self.status_update.emit("Terminating VPN process…")
        self._backend.disconnect()
        self.disconnected.emit()


# ──── MANAGER ──── #

class ConnectionManager(QObject):
    """High-level interface — spawns QThreads for connect/disconnect."""
    connected     = pyqtSignal()
    disconnected  = pyqtSignal()
    error         = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._thread:  QThread | None = None
        self._worker:  ConnectionWorker | None = None
        self._backend: VPNBackend | None = None
        self._profile: Profile | None = None

    # ──── PUBLIC ──── #

    def connect(self, profile: Profile) -> None:
        backend_cls = _BACKENDS.get(profile.protocol)
        if backend_cls is None:
            self.error.emit(f"Unknown protocol: {profile.protocol!r}")
            return
        self._backend = backend_cls()
        self._profile = profile
        self._start_worker("connect")

    def vpn_disconnect(self) -> None:
        if self._backend is None:
            return
        self._start_worker("disconnect")

    def is_connected(self) -> bool:
        return self._backend.is_connected() if self._backend else False

    def active_interface(self) -> str | None:
        """Return the tunnel interface name for the current connection."""
        return self._backend.interface_name() if self._backend else None

    # ──── PRIVATE ──── #

    def _start_worker(self, action: str) -> None:
        if self._thread and self._thread.isRunning():
            return

        self._thread = QThread()
        self._worker = ConnectionWorker(action, self._backend, self._profile)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.connected.connect(self.connected)
        self._worker.disconnected.connect(self.disconnected)
        self._worker.error.connect(self.error)
        self._worker.status_update.connect(self.status_update)
        self._worker.connected.connect(self._thread.quit)
        self._worker.disconnected.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        self._thread.start()
