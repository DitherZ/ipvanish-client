"""
ui/widgets/dashboard.py
Landing dashboard tab for IPVanish-Client v2.

Shows: full logo, tagline, exposed public IP + location with visual hierarchy,
Connect Now button, and credits. Switches to a live-stats view when connected.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSizePolicy, QScrollArea,
    QStackedWidget,
)

ASSETS_SVG = Path(__file__).parents[2] / "assets" / "SVG"


# ──── FULL LOGO ──── #

class FullLogoWidget(QWidget):
    def __init__(self, target_height: int = 150, parent=None):
        super().__init__(parent)
        self._dark = True
        self._renderer_dbg: QSvgRenderer | None = None
        self._renderer_wbg: QSvgRenderer | None = None
        self._aspect = 125.4 / 151.4

        for attr, name in [("_renderer_dbg", "full-logo_dbg.svg"),
                            ("_renderer_wbg", "full-logo_wbg.svg")]:
            p = ASSETS_SVG / name
            if p.exists():
                try:
                    r = QSvgRenderer(str(p))
                    vb = r.viewBoxF()
                    if vb.height() > 0:
                        self._aspect = vb.width() / vb.height()
                    setattr(self, attr, r)
                except Exception:
                    pass

        self.setFixedSize(int(target_height * self._aspect), target_height)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_dark(self, dark: bool):
        self._dark = dark
        self.update()

    def paintEvent(self, _event):  # noqa: N802
        renderer = self._renderer_dbg if self._dark else self._renderer_wbg
        if renderer is None:
            p = QPainter(self)
            p.setPen(QColor("#70bb43"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "IPVANISH")
            p.end()
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()


# ──── HELPERS ──── #

def _link(text: str, url: str) -> QLabel:
    lbl = QLabel(f'<a href="{url}" style="color:#70bb43; text-decoration:none;">{text}</a>')
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setOpenExternalLinks(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    return lbl


def _hline(color: str = "#70bb43", opacity: int = 60) -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(
        f"max-height:1px; min-height:1px; "
        f"background:rgba({int(color[1:3],16)},"
        f"{int(color[3:5],16)},{int(color[5:7],16)},{opacity}); border:none;"
    )
    return line


def _stat_box(title: str, value: str = "—") -> tuple[QWidget, QLabel]:
    """Returns (container_widget, value_label) for a titled stat card."""
    box = QFrame()
    box.setObjectName("card")
    lay = QVBoxLayout(box)
    lay.setContentsMargins(16, 12, 16, 12)
    lay.setSpacing(4)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    val = QLabel(value)
    val.setObjectName("statValue")
    val.setAlignment(Qt.AlignmentFlag.AlignCenter)
    ttl = QLabel(title)
    ttl.setObjectName("statTitle")
    ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(val)
    lay.addWidget(ttl)
    return box, val


# ──── DASHBOARD ──── #

class DashboardWidget(QWidget):
    connect_now = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark = True
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_disconnected_page())  # index 0
        self._stack.addWidget(self._build_connected_page())     # index 1
        self._stack.setCurrentIndex(0)

        outer.addWidget(self._stack)

    # ──── PAGE: DISCONNECTED ──── #

    def _build_disconnected_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 28, 40, 28)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Logo
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._logo = FullLogoWidget(target_height=148)
        logo_row.addWidget(self._logo)
        layout.addLayout(logo_row)

        layout.addSpacing(10)

        tagline = QLabel("Unofficial Linux GUI Client")
        tagline.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        tagline.setObjectName("dashTagline")
        layout.addWidget(tagline)

        layout.addSpacing(22)
        layout.addWidget(_hline("#70bb43", 80))
        layout.addSpacing(22)

        # Exposure
        exp_header = QLabel("YOUR CURRENT EXPOSURE")
        exp_header.setObjectName("dashSectionHeader")
        layout.addWidget(exp_header)

        layout.addSpacing(10)

        self._ip_label = QLabel("Fetching…")
        self._ip_label.setObjectName("dashIP")
        layout.addWidget(self._ip_label)

        layout.addSpacing(6)

        self._loc_label = QLabel("")
        self._loc_label.setObjectName("dashLocation")
        layout.addWidget(self._loc_label)

        self._isp_label = QLabel("")
        self._isp_label.setObjectName("dashISP")
        layout.addWidget(self._isp_label)

        layout.addSpacing(24)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._connect_btn = QPushButton("  →  Connect Now")
        self._connect_btn.setObjectName("connectBtn")
        self._connect_btn.setFixedWidth(220)
        self._connect_btn.clicked.connect(self.connect_now)
        btn_row.addWidget(self._connect_btn)
        layout.addLayout(btn_row)

        layout.addSpacing(28)
        layout.addWidget(_hline("#464c52", 120))
        layout.addSpacing(22)

        about_header = QLabel("ABOUT")
        about_header.setObjectName("dashSectionHeader")
        layout.addWidget(about_header)

        layout.addSpacing(10)

        disclaimer = QLabel(
            "This is an unofficial, open-source GUI client for the IPVanish VPN service.\n"
            "Not affiliated with, endorsed by, or supported by IPVanish or its parent company.\n"
            "All VPN infrastructure and service rights belong to IPVanish."
        )
        disclaimer.setObjectName("dashDisclaimer")
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        layout.addSpacing(16)

        for label_text, link_text, url in [
            ("VPN Service",   "ipvanish.com",
             "https://www.ipvanish.com/"),
            ("Client Author", "DitherZ",
             "https://www.github.com/DitherZ/IPVanish-Client-v2"),
            ("Source",        "github.com/DitherZ/IPVanish-Client-v2",
             "https://www.github.com/DitherZ/IPVanish-Client-v2"),
        ]:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            key = QLabel(label_text)
            key.setObjectName("dashCreditKey")
            key.setFixedWidth(120)
            row.addWidget(key)
            sep = QLabel("→")
            sep.setObjectName("dashCreditArrow")
            sep.setFixedWidth(24)
            row.addWidget(sep)
            row.addWidget(_link(link_text, url))
            row.addStretch()
            layout.addLayout(row)
            layout.addSpacing(4)

        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ──── PAGE: CONNECTED ──── #

    def _build_connected_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 28, 40, 28)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Logo (shared renderer, separate widget instance)
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._logo_conn = FullLogoWidget(target_height=100)
        logo_row.addWidget(self._logo_conn)
        layout.addLayout(logo_row)

        layout.addSpacing(8)

        # Connected indicator
        conn_row = QHBoxLayout()
        conn_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        conn_dot = QLabel("●")
        conn_dot.setStyleSheet("color: #3FB950; font-size: 14px;")
        conn_row.addWidget(conn_dot)
        self._conn_proto_label = QLabel("Connected via OpenVPN")
        self._conn_proto_label.setObjectName("dashTagline")
        self._conn_proto_label.setStyleSheet("color: #3FB950;")
        conn_row.addWidget(self._conn_proto_label)
        layout.addLayout(conn_row)

        layout.addSpacing(18)
        layout.addWidget(_hline("#3FB950", 80))
        layout.addSpacing(18)

        # VPN IP / location
        vpn_header = QLabel("YOUR VPN IDENTITY")
        vpn_header.setObjectName("dashSectionHeader")
        layout.addWidget(vpn_header)

        layout.addSpacing(10)

        self._vpn_ip_label = QLabel("—")
        self._vpn_ip_label.setObjectName("dashIP")
        layout.addWidget(self._vpn_ip_label)

        layout.addSpacing(6)

        self._vpn_loc_label = QLabel("")
        self._vpn_loc_label.setObjectName("dashLocation")
        layout.addWidget(self._vpn_loc_label)

        self._vpn_isp_label = QLabel("")
        self._vpn_isp_label.setObjectName("dashISP")
        layout.addWidget(self._vpn_isp_label)

        layout.addSpacing(8)

        self._vpn_server_label = QLabel("")
        self._vpn_server_label.setObjectName("dashDisclaimer")
        layout.addWidget(self._vpn_server_label)

        layout.addSpacing(22)
        layout.addWidget(_hline("#464c52", 100))
        layout.addSpacing(16)

        # Network stats row
        stats_header = QLabel("NETWORK STATS")
        stats_header.setObjectName("dashSectionHeader")
        layout.addWidget(stats_header)

        layout.addSpacing(12)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        up_box, self._stat_up     = _stat_box("UPLOAD")
        down_box, self._stat_down = _stat_box("DOWNLOAD")
        ping_box, self._stat_ping = _stat_box("SERVER")

        for box in (up_box, down_box, ping_box):
            box.setMinimumWidth(140)
            stats_row.addWidget(box)

        layout.addLayout(stats_row)

        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ──── PUBLIC API ──── #

    def set_geo(self, ip: str, city: str, country: str, isp: str):
        self._ip_label.setText(ip)
        loc = ", ".join(p for p in (city, country) if p) or "Unknown"
        self._loc_label.setText(f"📍  {loc}")
        self._isp_label.setText(f"🌐  {isp}" if isp else "")

    def set_geo_error(self):
        self._ip_label.setText("Unavailable")
        self._loc_label.setText("Could not determine location")
        self._isp_label.setText("")

    def set_connected(self, server: str, protocol: str = "OpenVPN"):
        self._conn_proto_label.setText(f"Connected via {protocol}")
        self._vpn_server_label.setText(f"Server:  {server}")
        self._vpn_ip_label.setText("Fetching…")
        self._vpn_loc_label.setText("")
        self._vpn_isp_label.setText("")
        self._stat_up.setText("—")
        self._stat_down.setText("—")
        self._stat_ping.setText(server)
        self._logo_conn.set_dark(self._dark)
        self._stack.setCurrentIndex(1)

    def set_disconnected(self):
        self._stack.setCurrentIndex(0)

    def update_connected_geo(self, ip: str, city: str, country: str, isp: str):
        self._vpn_ip_label.setText(ip)
        loc = ", ".join(p for p in (city, country) if p) or "Unknown"
        self._vpn_loc_label.setText(f"📍  {loc}")
        self._vpn_isp_label.setText(f"🌐  {isp}" if isp else "")

    def update_speed(self, up: str, down: str):
        self._stat_up.setText(up)
        self._stat_down.setText(down)

    def set_dark(self, dark: bool):
        self._dark = dark
        self._logo.set_dark(dark)
        self._logo_conn.set_dark(dark)
