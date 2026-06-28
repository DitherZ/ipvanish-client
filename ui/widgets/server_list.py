"""
ui/widgets/server_list.py
LocationsWidget — pill switcher, pinned Favorites, distance-sorted lists.
IPVanish-Client v2
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QLineEdit, QLabel, QFrame, QPushButton,
)

from core.favorites import FavoritesManager
from core.profiles import ProfileStore, Profile
from core.servers import nations, cities

_BADGE = {"openvpn": "[OVP]", "wireguard": "[WG]"}


class LocationsWidget(QWidget):
    """
    Locations panel with pill switcher (Countries / Cities).
    Lists default to the order in modules/servers.py; call
    set_sorted_lists() once geo data is available to re-order
    nearest → furthest from the user.
    """

    server_selected = pyqtSignal(str, str, str)   # (name, mode, protocol)

    def __init__(self, favorites: FavoritesManager, parent=None):
        super().__init__(parent)
        self._favorites    = favorites
        self._active_mode  = "country"
        self._nations      = list(nations)
        self._cities       = list(cities)
        self._store        = ProfileStore()
        self._build_ui()
        self._refresh_favorites()
        self._show_mode("country")
        self.refresh_imported()

    # ──── BUILD ──── #

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Search bar
        self._search = QLineEdit()
        self._search.setObjectName("searchBox")
        self._search.setPlaceholderText("  🔍  Search…")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        # Pill switcher
        pill_row = QHBoxLayout()
        pill_row.setSpacing(0)
        pill_row.setContentsMargins(0, 2, 0, 2)

        self._pill_countries = QPushButton("Countries")
        self._pill_countries.setObjectName("pillBtn")
        self._pill_countries.clicked.connect(lambda: self._show_mode("country"))

        self._pill_cities = QPushButton("Cities")
        self._pill_cities.setObjectName("pillBtn")
        self._pill_cities.clicked.connect(lambda: self._show_mode("city"))

        pill_row.addWidget(self._pill_countries)
        pill_row.addWidget(self._pill_cities)
        pill_row.addStretch()
        layout.addLayout(pill_row)

        # Favorites pinned section
        self._fav_label = QLabel("  ★  Favorites")
        self._fav_label.setObjectName("sectionTitle")
        self._fav_label.setContentsMargins(2, 4, 0, 0)
        layout.addWidget(self._fav_label)

        self._fav_list = QListWidget()
        self._fav_list.setAlternatingRowColors(False)
        self._fav_list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._fav_list)

        self._divider = QFrame()
        self._divider.setFrameShape(QFrame.Shape.HLine)
        self._divider.setObjectName("accentLine")
        self._divider.setStyleSheet(
            "max-height:1px; min-height:1px; background:#70bb43; border:none;"
        )
        layout.addWidget(self._divider)

        # All servers label + list
        self._all_label = QLabel("  All Countries")
        self._all_label.setObjectName("sectionTitle")
        self._all_label.setContentsMargins(2, 4, 0, 0)
        layout.addWidget(self._all_label)

        self._server_list = QListWidget()
        self._server_list.setAlternatingRowColors(False)
        self._server_list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._server_list)

        # Imported profiles section (hidden when empty)
        self._imported_divider = QFrame()
        self._imported_divider.setFrameShape(QFrame.Shape.HLine)
        self._imported_divider.setStyleSheet(
            "max-height:1px; min-height:1px; background:#3D4758; border:none;"
        )
        layout.addWidget(self._imported_divider)

        self._imported_label = QLabel("  Imported Profiles")
        self._imported_label.setObjectName("sectionTitle")
        self._imported_label.setContentsMargins(2, 4, 0, 0)
        layout.addWidget(self._imported_label)

        self._imported_list = QListWidget()
        self._imported_list.setAlternatingRowColors(False)
        self._imported_list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._imported_list)

        self._imported_divider.setVisible(False)
        self._imported_label.setVisible(False)
        self._imported_list.setVisible(False)

    # ──── MODE SWITCH ──── #

    def _show_mode(self, mode: str):
        self._active_mode = mode

        self._pill_countries.setProperty("active", "true"  if mode == "country" else "false")
        self._pill_cities.setProperty(   "active", "true"  if mode == "city"    else "false")
        for btn in (self._pill_countries, self._pill_cities):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._all_label.setText(
            "  All Countries" if mode == "country" else "  All Cities"
        )
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)

        src = self._nations if mode == "country" else self._cities
        self._populate_all(src)
        self._refresh_favorites()

    # ──── POPULATE ──── #

    def _populate_all(self, items: list[str]):
        self._server_list.clear()
        for name in items:
            self._server_list.addItem(self._make_item(name, self._active_mode))

    def _refresh_favorites(self):
        mode = self._active_mode
        favs = [f["name"] for f in self._favorites.all() if f["mode"] == mode]

        self._fav_list.clear()
        for name in favs:
            item = QListWidgetItem(f"  ★  {name}")
            item.setData(Qt.ItemDataRole.UserRole,     name)
            item.setData(Qt.ItemDataRole.UserRole + 1, mode)
            self._fav_list.addItem(item)

        visible = len(favs) > 0
        self._fav_label.setVisible(visible)
        self._fav_list.setVisible(visible)
        self._divider.setVisible(visible)
        if visible:
            row_h = max(self._fav_list.sizeHintForRow(0), 28)
            self._fav_list.setFixedHeight(row_h * len(favs) + 6)

    def _make_item(self, name: str, mode: str, protocol: str = "openvpn") -> QListWidgetItem:
        starred = self._favorites.exists(name, mode)
        item = QListWidgetItem(f"  {'★' if starred else '☆'}  {name}")
        item.setData(Qt.ItemDataRole.UserRole,     name)
        item.setData(Qt.ItemDataRole.UserRole + 1, mode)
        item.setData(Qt.ItemDataRole.UserRole + 2, protocol)
        return item

    # ──── FILTER ──── #

    def _filter(self, text: str):
        text = text.strip().lower()
        src  = self._nations if self._active_mode == "country" else self._cities
        filtered = [n for n in src if text in n.lower()] if text else src
        self._populate_all(filtered)

    # ──── EVENTS ──── #

    def _on_double_click(self, item: QListWidgetItem):
        name     = item.data(Qt.ItemDataRole.UserRole)
        mode     = item.data(Qt.ItemDataRole.UserRole + 1) or self._active_mode
        protocol = item.data(Qt.ItemDataRole.UserRole + 2) or "openvpn"
        self.server_selected.emit(name, mode, protocol)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            for lst in (self._fav_list, self._server_list):
                item = lst.currentItem()
                if item:
                    self._on_double_click(item)
                    return
        super().keyPressEvent(event)

    # ──── PUBLIC API ──── #

    def set_sorted_lists(self, sorted_nations: list[str], sorted_cities: list[str]):
        """Re-order lists after geo lookup resolves (nearest → furthest)."""
        self._nations = sorted_nations
        self._cities  = sorted_cities
        src = self._nations if self._active_mode == "country" else self._cities
        self._populate_all(src)

    def refresh_imported(self) -> None:
        """Rebuild the Imported Profiles section from ProfileStore."""
        profiles = [p for p in self._store.scan() if not p.is_ipvanish]
        self._imported_list.clear()
        for p in profiles:
            badge = _BADGE.get(p.protocol, "[?]")
            item = QListWidgetItem(f"  {badge}  {p.name}")
            item.setData(Qt.ItemDataRole.UserRole,     p.name)
            item.setData(Qt.ItemDataRole.UserRole + 1, "imported")
            item.setData(Qt.ItemDataRole.UserRole + 2, p.protocol)
            self._imported_list.addItem(item)

        has = len(profiles) > 0
        self._imported_divider.setVisible(has)
        self._imported_label.setVisible(has)
        self._imported_list.setVisible(has)
        if has:
            row_h = max(self._imported_list.sizeHintForRow(0), 28)
            self._imported_list.setFixedHeight(row_h * len(profiles) + 6)

    def refresh_after_favorite_change(self):
        """Rebuild pinned section and redraw ★/☆ glyphs in the main list."""
        self._refresh_favorites()
        for i in range(self._server_list.count()):
            it      = self._server_list.item(i)
            name    = it.data(Qt.ItemDataRole.UserRole)
            mode    = it.data(Qt.ItemDataRole.UserRole + 1) or self._active_mode
            starred = self._favorites.exists(name, mode)
            it.setText(f"  {'★' if starred else '☆'}  {name}")
