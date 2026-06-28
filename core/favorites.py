"""
core/favorites.py
Persistent favorites store for IPVanish-Client v2.
Serialized as JSON at $HOME/.config/ipvanish-client/favorites.json
"""

import json
from pathlib import Path


FAVORITES_FILE = Path.home() / ".config" / "ipvanish-client" / "favorites.json"


class FavoritesManager:
    """
    Stores favorites as a list of dicts:
        [{"name": "New York", "mode": "city"}, ...]
    """

    def __init__(self):
        FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._data: list[dict] = self._load()

    # ──── PUBLIC API ──── #

    def add(self, name: str, mode: str):
        if not self.exists(name, mode):
            self._data.append({"name": name, "mode": mode})
            self._save()

    def remove(self, name: str, mode: str):
        self._data = [
            f for f in self._data
            if not (f["name"] == name and f["mode"] == mode)
        ]
        self._save()

    def exists(self, name: str, mode: str) -> bool:
        return any(f["name"] == name and f["mode"] == mode for f in self._data)

    def all(self) -> list[dict]:
        return list(self._data)

    def toggle(self, name: str, mode: str):
        if self.exists(name, mode):
            self.remove(name, mode)
        else:
            self.add(name, mode)

    # ──── PRIVATE ──── #

    def _load(self) -> list[dict]:
        if FAVORITES_FILE.exists():
            try:
                return json.loads(FAVORITES_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self):
        FAVORITES_FILE.write_text(json.dumps(self._data, indent=2))
