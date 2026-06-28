"""
ui/widgets/status_panel.py
Live connection stats panel: state indicator, elapsed time, server name, public IP.
IPVanish-Client v2
"""

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QFrame,
)


class StatBox(QWidget):
    def __init__(self, title: str, initial: str = "—", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._value = QLabel(initial)
        self._value.setObjectName("statValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel(title)
        self._title.setObjectName("statTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._value)
        layout.addWidget(self._title)
        self.setObjectName("card")

    def set_value(self, text: str):
        self._value.setText(text)


class StatusPanel(QWidget):
    """
    Compact status bar shown at the bottom of the main window.
    Tracks: connection state, elapsed time, server name, public IP.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self._connected = False
        self._start_time: float | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._build_ui()

    # ──── BUILD ──── #

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(12)

        # Dot indicator
        self._dot = QLabel("●")
        self._dot.setFixedWidth(20)
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dot.setStyleSheet("color: #3D4758; font-size: 16px;")
        layout.addWidget(self._dot)

        # Status text
        self._status_text = QLabel("Not connected")
        self._status_text.setObjectName("statusLabel")
        layout.addWidget(self._status_text)

        layout.addStretch()

        # Stat boxes
        self._server_box = StatBox("SERVER")
        self._time_box = StatBox("DURATION")
        self._ip_box = StatBox("PUBLIC IP")

        for box in (self._server_box, self._time_box, self._ip_box):
            box.setMinimumWidth(140)
            layout.addWidget(box)

    # ──── PUBLIC API ──── #

    def set_connecting(self, message: str = "Connecting…"):
        self._dot.setStyleSheet("color: #D29922; font-size: 16px;")
        self._status_text.setObjectName("statusLabel")
        self._status_text.setText(message)
        self._status_text.style().unpolish(self._status_text)
        self._status_text.style().polish(self._status_text)

    def set_connected(self, server: str, public_ip: str = "fetching…", protocol: str = ""):
        self._connected = True
        self._start_time = time.time()
        self._dot.setStyleSheet("color: #3FB950; font-size: 16px;")
        self._status_text.setObjectName("statusConnected")
        self._status_text.setText("Connected")
        self._status_text.style().unpolish(self._status_text)
        self._status_text.style().polish(self._status_text)
        display = f"{server}  [{protocol}]" if protocol else server
        self._server_box.set_value(display)
        self._ip_box.set_value(public_ip)
        self._time_box.set_value("00:00:00")
        self._timer.start()

    def set_disconnected(self):
        self._connected = False
        self._timer.stop()
        self._dot.setStyleSheet("color: #3D4758; font-size: 16px;")
        self._status_text.setObjectName("statusLabel")
        self._status_text.setText("Not connected")
        self._status_text.style().unpolish(self._status_text)
        self._status_text.style().polish(self._status_text)
        self._server_box.set_value("—")
        self._time_box.set_value("—")
        self._ip_box.set_value("—")

    def update_ip(self, ip: str):
        self._ip_box.set_value(ip)

    # ──── PRIVATE ──── #

    def _tick(self):
        if self._start_time is None:
            return
        elapsed = int(time.time() - self._start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self._time_box.set_value(f"{h:02d}:{m:02d}:{s:02d}")
