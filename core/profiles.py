"""
core/profiles.py
Profile dataclass and ProfileStore — protocol-agnostic VPN config management.
IPVanish-Client v2
"""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

CONFIGS_DIR   = Path(__file__).parents[1] / "config"
IPVANISH_DIR  = CONFIGS_DIR / "ipvanish"
IMPORTED_DIR  = CONFIGS_DIR / "imported"

# IPVanish filename pattern: ipvanish-CC-City-Name-hst-NNN.ovpn
_IPVANISH_RE = re.compile(
    r"^ipvanish-([A-Z]{2})-(.+?)-[a-z]{3}-[a-z]\d+\.ovpn$", re.IGNORECASE
)

IFNAMSIZ = 15  # Linux kernel interface name length limit


@dataclass(frozen=True)
class Profile:
    name: str                               # display name (city or file stem)
    protocol: Literal["openvpn", "wireguard"]
    path: Path                              # absolute path to the config file
    location_hint: str | None              # "City, CC" or None
    is_ipvanish: bool                      # True when sourced from IPVANISH_DIR


class ProfileStore:
    """
    Scans config/ipvanish/ and config/imported/ for usable VPN profiles.
    On first call, migrates any flat config/*.ovpn files into config/ipvanish/.
    """

    def __init__(self) -> None:
        self._profiles: list[Profile] = []

    # ──── PUBLIC ──── #

    def scan(self) -> list[Profile]:
        """Return all known profiles; runs first-time migration if needed."""
        self._maybe_migrate()
        self._profiles = []
        self._scan_ipvanish()
        self._scan_imported()
        return list(self._profiles)

    def import_file(self, src: Path) -> Profile:
        """
        Copy a .ovpn or .conf file into config/imported/ and return its Profile.
        For WireGuard .conf files: validates stem ≤ 15 chars; truncates + warns
        if longer; appends _N suffix on name collision.
        """
        IMPORTED_DIR.mkdir(parents=True, exist_ok=True)

        protocol: Literal["openvpn", "wireguard"] = (
            "wireguard" if src.suffix.lower() == ".conf" else "openvpn"
        )

        stem = src.stem
        if protocol == "wireguard" and len(stem) > IFNAMSIZ:
            stem = stem[:IFNAMSIZ]
            logger.warning(
                "WireGuard interface name truncated to %d chars: %r", IFNAMSIZ, stem
            )

        # Resolve collisions
        dest_name = stem + src.suffix
        dest = IMPORTED_DIR / dest_name
        counter = 1
        while dest.exists():
            dest_name = f"{stem[:IFNAMSIZ - len(str(counter)) - 1]}_{counter}{src.suffix}"
            dest = IMPORTED_DIR / dest_name
            counter += 1

        shutil.copy2(src, dest)
        logger.info("Imported profile: %s → %s", src, dest)

        return Profile(
            name=dest.stem,
            protocol=protocol,
            path=dest,
            location_hint=None,
            is_ipvanish=False,
        )

    def get_ipvanish_profiles(self) -> list[Profile]:
        return [p for p in self._profiles if p.is_ipvanish]

    def get_imported_profiles(self) -> list[Profile]:
        return [p for p in self._profiles if not p.is_ipvanish]

    def find_by_name_mode(self, name: str, mode: str) -> Profile | None:
        """Look up an IPVanish profile by display name and mode (country/city)."""
        for p in self._profiles:
            if p.is_ipvanish and p.name == name:
                return p
        return None

    # ──── PRIVATE ──── #

    def _scan_ipvanish(self) -> None:
        if not IPVANISH_DIR.exists():
            return
        for path in sorted(IPVANISH_DIR.glob("*.ovpn")):
            m = _IPVANISH_RE.match(path.name)
            if m:
                country_code = m.group(1).upper()
                raw_city = m.group(2).replace("-", " ").title()
                hint = f"{raw_city}, {country_code}"
                name = raw_city
            else:
                hint = None
                name = path.stem
            self._profiles.append(Profile(
                name=name,
                protocol="openvpn",
                path=path,
                location_hint=hint,
                is_ipvanish=True,
            ))

    def _scan_imported(self) -> None:
        if not IMPORTED_DIR.exists():
            return
        for path in sorted(IMPORTED_DIR.iterdir()):
            if path.suffix.lower() == ".conf":
                protocol: Literal["openvpn", "wireguard"] = "wireguard"
            elif path.suffix.lower() == ".ovpn":
                protocol = "openvpn"
            else:
                continue
            self._profiles.append(Profile(
                name=path.stem,
                protocol=protocol,
                path=path,
                location_hint=None,
                is_ipvanish=False,
            ))

    def _maybe_migrate(self) -> None:
        """
        First-run migration: move flat config/*.ovpn into config/ipvanish/.
        Skips conn.ovpn (runtime-generated). Copies first, verifies count,
        then removes originals. Logs everything.
        """
        if IPVANISH_DIR.exists():
            return  # already migrated or fresh install

        flat_ovpn = [
            p for p in CONFIGS_DIR.glob("*.ovpn")
            if p.name != "conn.ovpn"
        ]
        if not flat_ovpn:
            return  # nothing to migrate

        logger.info(
            "Migrating %d flat .ovpn files → config/ipvanish/", len(flat_ovpn)
        )
        IPVANISH_DIR.mkdir(parents=True, exist_ok=True)

        copied: list[Path] = []
        for src in flat_ovpn:
            dest = IPVANISH_DIR / src.name
            shutil.copy2(src, dest)
            copied.append(src)

        # Verify before removing
        migrated_count = len(list(IPVANISH_DIR.glob("*.ovpn")))
        if migrated_count >= len(flat_ovpn):
            for src in copied:
                src.unlink()
            logger.info(
                "Migration complete: %d files moved, originals removed.", migrated_count
            )
        else:
            logger.error(
                "Migration copy count mismatch (%d copied vs %d expected) — "
                "originals kept in place.",
                migrated_count, len(flat_ovpn),
            )
