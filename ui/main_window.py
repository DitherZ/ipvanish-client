"""
ui/main_window.py
Main application window — IPVanish-Client v2.
Dashboard | Locations | Settings  ·  Dual theme  ·  System tray  ·  Geo sort
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QFrame,
    QCheckBox, QMessageBox, QApplication,
    QSystemTrayIcon, QMenu, QScrollArea,
)

from core.connection import ConnectionManager
from core.config_parser import ConfigParser
from core.favorites import FavoritesManager
from core.geo import GeoManager, GeoWorker, sort_by_distance, COUNTRY_CITY
from core.profiles import Profile, ProfileStore, CONFIGS_DIR
from core.tunnel_monitor import TunnelMonitor
from core.servers import nations, cities
from ui.widgets.dashboard import DashboardWidget
from ui.widgets.server_list import LocationsWidget
from ui.widgets.status_panel import StatusPanel
from ui.widgets.credentials_tab import CredentialsTab
from ui.widgets.configs_tab import ConfigsTab

ASSETS_SVG = Path(__file__).parents[1] / "assets" / "SVG"
ASSETS_PNG = Path(__file__).parents[1] / "assets" / "PNG"
ASSETS     = ASSETS_SVG

TAB_DASHBOARD = 0
TAB_LOCATIONS = 1
TAB_SETTINGS  = 2


# ──── SVG LOGO (header text logo) ──── #

class SvgLogoWidget(QWidget):
    def __init__(self, target_height: int = 46, parent=None):
        super().__init__(parent)
        self._dark   = True
        self._aspect = 3.015
        self._renderer_dbg: QSvgRenderer | None = None
        self._renderer_wbg: QSvgRenderer | None = None

        for attr, name in [("_renderer_dbg", "text-logo_dbg.svg"),
                            ("_renderer_wbg", "text-logo_wbg.svg")]:
            p = ASSETS / name
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

    def set_dark(self, dark: bool):
        self._dark = dark
        self.update()

    def paintEvent(self, event):
        renderer = self._renderer_dbg if self._dark else self._renderer_wbg
        if renderer is None:
            p = QPainter(self)
            p.setPen(QColor("#70bb43"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter, "IPVANISH")
            p.end()
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()


# ──── WINDOW ICON ──── #

def build_window_icon() -> QIcon:
    png = ASSETS_PNG / "IPVanish_icon_512x512.png"
    return QIcon(str(png)) if png.exists() else QIcon()


# ──── MAIN WINDOW ──── #

class MainWindow(QMainWindow):

    DARK  = "dark"
    LIGHT = "light"

    def __init__(self):
        super().__init__()
        self._theme          = self.DARK
        self._favorites      = FavoritesManager()
        self._connection     = ConnectionManager()
        self._config_parser  = ConfigParser()
        self._geo            = GeoManager()
        self._tunnel_mon     = TunnelMonitor(self)
        self._store          = ProfileStore()
        self._auto_reconnect = False
        self._close_to_tray  = True
        self._current_server:   str | None     = None
        self._current_mode:     str | None     = None
        self._current_profile:  Profile | None = None
        self._public_ip: str             = "Unknown"
        self._tray_up:   str             = "—"
        self._tray_down: str             = "—"

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(15_000)
        self._reconnect_timer.timeout.connect(self._check_reconnect)

        self._setup_window()
        self._setup_tray()
        self._build_ui()
        self._connect_signals()
        self._apply_theme(self._theme)

        # Kick off geo lookup — populates dashboard + sorts location lists
        self._geo.fetch()

    # ──── WINDOW SETUP ──── #

    def _setup_window(self):
        self.setWindowTitle("IPVanish Client")
        self.setMinimumSize(700, 580)
        self.resize(820, 700)
        icon = build_window_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
            QApplication.instance().setWindowIcon(icon)

    # ──── SYSTEM TRAY ──── #

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        icon = build_window_icon()
        self._tray.setIcon(icon if not icon.isNull() else
            self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        self._tray_menu = QMenu()
        self._tray_menu.addAction("Show").triggered.connect(self._restore_from_tray)
        self._tray_menu.addSeparator()
        self._tray_conn_action = self._tray_menu.addAction("Connect")
        self._tray_conn_action.triggered.connect(self._on_connect_clicked)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction("Quit").triggered.connect(QApplication.instance().quit)

        self._tray.setContextMenu(self._tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._update_tray_tooltip()
        self._tray.show()

    def _update_tray_tooltip(self):
        connected = self._connection.is_connected()
        if connected:
            tip = (
                f"IPVanish Client\n"
                f"Status:  Connected  →  {self._current_server or '—'}\n"
                f"IP:      {self._public_ip}\n"
                f"↑  {self._tray_up}    ↓  {self._tray_down}"
            )
        else:
            tip = (
                f"IPVanish Client\n"
                f"Status:  Not connected\n"
                f"Exposed IP:  {self._public_ip}"
            )
        self._tray.setToolTip(tip)

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        if self._close_to_tray and self._tray.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self._tray.showMessage(
                "IPVanish Client", "Running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information, 2000,
            )
        else:
            self._tray.hide()
            event.accept()

    # ──── UI BUILD ──── #

    def _build_ui(self):
        # Outer border frame — 1px IPVanish green outline
        border_frame = QFrame()
        border_frame.setObjectName("windowBorder")
        self.setCentralWidget(border_frame)

        border_layout = QVBoxLayout(border_frame)
        border_layout.setContentsMargins(1, 1, 1, 1)
        border_layout.setSpacing(0)

        root = QWidget()
        border_layout.addWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        accent = QFrame()
        accent.setObjectName("accentLine")
        root_layout.addWidget(accent)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 12, 14, 0)
        body_layout.setSpacing(0)
        self._tabs = self._build_tabs()
        body_layout.addWidget(self._tabs)
        root_layout.addWidget(body, stretch=1)

        root_layout.addWidget(self._build_connect_bar())
        self._status_panel = StatusPanel()
        root_layout.addWidget(self._status_panel)

    # ──── HEADER ──── #

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        self._logo = SvgLogoWidget(target_height=46)
        layout.addWidget(self._logo)
        layout.addStretch()

        self._theme_btn = QPushButton("☀  Light")
        self._theme_btn.setObjectName("themeBtn")
        self._theme_btn.setToolTip("Switch theme")
        self._theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self._theme_btn)

        return header

    # ──── TABS ──── #

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_dashboard_tab(), "Dashboard")
        tabs.addTab(self._build_locations_tab(), "Locations")
        tabs.addTab(self._build_settings_tab(),  "Settings")
        return tabs

    def _build_dashboard_tab(self) -> QWidget:
        self._dashboard = DashboardWidget()
        self._dashboard.connect_now.connect(
            lambda: self._tabs.setCurrentIndex(TAB_LOCATIONS)
        )
        return self._dashboard

    def _build_locations_tab(self) -> QWidget:
        self._locations = LocationsWidget(self._favorites)
        self._locations.server_selected.connect(self._on_server_selected)
        return self._locations

    def _build_settings_tab(self) -> QWidget:
        from ui.widgets.dashboard import _hline

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 28, 40, 28)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Behaviour ──
        bh = QLabel("BEHAVIOUR")
        bh.setObjectName("dashSectionHeader")
        layout.addWidget(bh)
        layout.addSpacing(12)

        self._auto_reconnect_cb = QCheckBox("Auto-reconnect on drop")
        self._auto_reconnect_cb.setChecked(False)
        self._auto_reconnect_cb.stateChanged.connect(self._toggle_auto_reconnect)
        layout.addWidget(self._auto_reconnect_cb)
        layout.addSpacing(8)

        self._close_to_tray_cb = QCheckBox("Close to system tray")
        self._close_to_tray_cb.setChecked(True)
        self._close_to_tray_cb.stateChanged.connect(
            lambda s: setattr(self, "_close_to_tray", bool(s))
        )
        layout.addWidget(self._close_to_tray_cb)

        layout.addSpacing(28)
        layout.addWidget(_hline("#464c52", 120))
        layout.addSpacing(24)

        # ── Account Credentials ──
        ch = QLabel("ACCOUNT CREDENTIALS")
        ch.setObjectName("dashSectionHeader")
        layout.addWidget(ch)
        layout.addSpacing(12)

        self._creds_tab = CredentialsTab()
        layout.addWidget(self._creds_tab)

        layout.addSpacing(28)
        layout.addWidget(_hline("#464c52", 120))
        layout.addSpacing(24)

        # ── OpenVPN Config Files ──
        cfh = QLabel("OPENVPN CONFIG FILES")
        cfh.setObjectName("dashSectionHeader")
        layout.addWidget(cfh)
        layout.addSpacing(12)

        self._configs_tab = ConfigsTab()
        self._configs_tab.profile_imported.connect(self._locations.refresh_imported)
        layout.addWidget(self._configs_tab)

        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        return lbl

    # ──── CONNECT BAR ──── #

    def _build_connect_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("connectBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        self._selection_label = QLabel("No server selected")
        self._selection_label.setObjectName("statusLabel")
        layout.addWidget(self._selection_label)
        layout.addStretch()

        self._fav_btn = QPushButton("☆")
        self._fav_btn.setObjectName("favBtn")
        self._fav_btn.setToolTip("Toggle favourite")
        self._fav_btn.clicked.connect(self._toggle_favorite)
        self._fav_btn.setVisible(False)
        layout.addWidget(self._fav_btn)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setObjectName("connectBtn")
        self._connect_btn.setEnabled(False)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self._connect_btn)

        return bar

    # ──── THEME ──── #

    def _apply_theme(self, theme: str):
        self._theme = theme
        self._logo.set_dark(theme == self.DARK)
        self._dashboard.set_dark(theme == self.DARK)
        self._theme_btn.setText("☀  Light" if theme == self.DARK else "🌙  Dark")
        self._stamp_theme(self, theme)

    def _stamp_theme(self, widget: QWidget, theme: str):
        widget.setProperty("theme", theme)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
        for child in widget.findChildren(QWidget):
            child.setProperty("theme", theme)
            child.style().unpolish(child)
            child.style().polish(child)
            child.update()

    @pyqtSlot()
    def _toggle_theme(self):
        self._apply_theme(self.LIGHT if self._theme == self.DARK else self.DARK)

    # ──── SIGNALS ──── #

    def _connect_signals(self):
        self._connection.connected.connect(self._on_connected)
        self._connection.disconnected.connect(self._on_disconnected)
        self._connection.error.connect(self._on_connection_error)
        self._connection.status_update.connect(self._status_panel.set_connecting)
        self._geo.result.connect(self._on_geo_result)
        self._geo.error.connect(self._on_geo_error)
        self._tunnel_mon.speed_update.connect(self._on_speed_update)

    # ──── GEO ──── #

    @pyqtSlot(object)
    def _on_geo_result(self, geo):
        self._public_ip = geo.ip
        self._dashboard.set_geo(geo.ip, geo.city, geo.country, geo.isp)
        self._update_tray_tooltip()
        if geo.lat != 0 or geo.lon != 0:
            sorted_nations = sort_by_distance(list(nations), geo.lat, geo.lon, COUNTRY_CITY)
            sorted_cities  = sort_by_distance(list(cities),  geo.lat, geo.lon)
            self._locations.set_sorted_lists(sorted_nations, sorted_cities)

    @pyqtSlot(str)
    def _on_geo_error(self, _msg: str):
        self._dashboard.set_geo_error()

    # ──── SERVER SELECTION ──── #

    @pyqtSlot(str, str, str)
    def _on_server_selected(self, name: str, mode: str, protocol: str):
        self._current_server = name
        self._current_mode   = mode
        self._selection_label.setText(f"Selected:  {name}")
        self._connect_btn.setEnabled(True)
        # Only show favourite button for IPVanish entries (not imported profiles)
        is_imported = (mode == "imported")
        self._fav_btn.setVisible(not is_imported)
        if not is_imported:
            self._update_fav_btn()
        # Pre-resolve imported profiles; IPVanish profiles resolved at connect time
        if is_imported:
            imported = [p for p in self._store.scan() if not p.is_ipvanish and p.name == name]
            self._current_profile = imported[0] if imported else None
        else:
            self._current_profile = None  # resolved in _do_connect from IPVanish dir
        # Update WireGuard hint in credentials tab
        self._creds_tab.set_wireguard_mode(protocol == "wireguard")

    def _toggle_favorite(self):
        if not self._current_server or not self._current_mode:
            return
        self._favorites.toggle(self._current_server, self._current_mode)
        self._update_fav_btn()
        self._locations.refresh_after_favorite_change()

    def _update_fav_btn(self):
        if not self._current_server or not self._current_mode:
            return
        starred = self._favorites.exists(self._current_server, self._current_mode)
        self._fav_btn.setText("★" if starred else "☆")
        self._fav_btn.setProperty("starred", "true" if starred else "false")
        self._fav_btn.style().unpolish(self._fav_btn)
        self._fav_btn.style().polish(self._fav_btn)

    # ──── CONNECT / DISCONNECT ──── #

    def _on_connect_clicked(self):
        if self._connection.is_connected():
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        if not self._current_server:
            QMessageBox.warning(self, "No Server",
                "Please select a server in the Locations tab first.")
            return

        profile = self._current_profile  # set for imported profiles

        if profile is None:
            # IPVanish profile — resolve via config_parser
            if not self._creds_tab.has_credentials():
                QMessageBox.warning(self, "No Credentials",
                    "Please enter your IPVanish credentials in Settings.")
                return
            try:
                chosen = self._config_parser.build(
                    self._current_server, self._current_mode or "city"
                )
            except FileNotFoundError as e:
                QMessageBox.critical(self, "Config Error", str(e))
                return
            # Resolve to a Profile so the backend receives proper metadata
            conn_path = CONFIGS_DIR / "conn.ovpn"
            profile = Profile(
                name=self._current_server,
                protocol="openvpn",
                path=conn_path,
                location_hint=None,
                is_ipvanish=True,
            )
        elif profile.protocol == "openvpn" and profile.is_ipvanish:
            # Imported IPVanish-style OVPN — still needs credentials
            if not self._creds_tab.has_credentials():
                QMessageBox.warning(self, "No Credentials",
                    "Please enter your IPVanish credentials in Settings.")
                return
            self._config_parser.build_from_path(profile.path, is_ipvanish=True)

        self._connect_btn.setEnabled(False)
        self._status_panel.set_connecting("Initiating connection…")
        self._current_profile = profile
        self._connection.connect(profile)

    def _do_disconnect(self):
        self._connect_btn.setEnabled(False)
        self._status_panel.set_connecting("Disconnecting…")
        self._connection.vpn_disconnect()

    @pyqtSlot()
    def _on_connected(self):
        self._connect_btn.setText("Disconnect")
        self._connect_btn.setProperty("connected", "true")
        self._connect_btn.setEnabled(True)
        self._refresh_btn_style(self._connect_btn)
        protocol = self._current_profile.protocol if self._current_profile else "openvpn"
        proto_label = "WireGuard" if protocol == "wireguard" else "OpenVPN"
        self._status_panel.set_connected(self._current_server or "Unknown", protocol=proto_label)
        self._dashboard.set_connected(self._current_server or "Unknown", proto_label)
        self._tray_conn_action.setText("Disconnect")
        iface = self._connection.active_interface() or "tun0"
        self._tunnel_mon.start(iface)
        self._fetch_connected_ip()

    @pyqtSlot()
    def _on_disconnected(self):
        self._connect_btn.setText("Connect")
        self._connect_btn.setProperty("connected", "false")
        self._connect_btn.setEnabled(True)
        self._refresh_btn_style(self._connect_btn)
        self._status_panel.set_disconnected()
        self._dashboard.set_disconnected()
        self._tray_conn_action.setText("Connect")
        self._tunnel_mon.stop()
        self._tray_up = self._tray_down = "—"
        self._update_tray_tooltip()

    @pyqtSlot(str)
    def _on_connection_error(self, msg: str):
        self._connect_btn.setEnabled(True)
        self._status_panel.set_disconnected()
        self._tray_conn_action.setText("Connect")
        self._tunnel_mon.stop()
        QMessageBox.critical(self, "Connection Error", f"An error occurred:\n\n{msg}")

    @staticmethod
    def _refresh_btn_style(btn: QPushButton):
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    # ──── SPEED + IP (post-connect) ──── #

    @pyqtSlot(str, str)
    def _on_speed_update(self, up: str, down: str):
        self._tray_up   = up
        self._tray_down = down
        self._dashboard.update_speed(up, down)
        self._update_tray_tooltip()

    def _fetch_connected_ip(self):
        """Re-fetch public IP after connecting (will show VPN IP)."""
        self._ip_thread = QThread()
        self._ip_worker = GeoWorker()
        self._ip_worker.moveToThread(self._ip_thread)
        self._ip_thread.started.connect(self._ip_worker.run)
        self._ip_worker.result.connect(self._on_connected_ip)
        self._ip_worker.result.connect(self._ip_thread.quit)
        self._ip_worker.error.connect(self._ip_thread.quit)
        self._ip_thread.start()

    @pyqtSlot(object)
    def _on_connected_ip(self, geo):
        self._public_ip = geo.ip
        self._status_panel.update_ip(geo.ip)
        self._dashboard.update_connected_geo(geo.ip, geo.city, geo.country, geo.isp)
        self._update_tray_tooltip()

    # ──── AUTO-RECONNECT ──── #

    def _toggle_auto_reconnect(self, state: int):
        self._auto_reconnect = bool(state)
        if self._auto_reconnect:
            self._reconnect_timer.start()
        else:
            self._reconnect_timer.stop()

    def _check_reconnect(self):
        if self._auto_reconnect and not self._connection.is_connected():
            if self._current_server:
                self._do_connect()
