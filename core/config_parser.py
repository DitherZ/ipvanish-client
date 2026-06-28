"""
core/config_parser.py
Parses and prepares an .ovpn configuration file for connection.
IPVanish-Client v2
"""

from __future__ import annotations

import random
from pathlib import Path

from core.servers import nations_dict, region_map

IPVANISH_DIR = Path(__file__).parents[1] / "config" / "ipvanish"
CONFIGS_DIR  = Path(__file__).parents[1] / "config"


class ConfigParser:
    """
    Selects a random IPVanish server matching the user's choice and writes
    a ready-to-use conn.ovpn into config/. Also used to prepare third-party
    .ovpn files — cert/cred injection is conditional, not forced.
    """

    def __init__(self) -> None:
        self.filelist: list[str] = []

    # ──── PUBLIC ──── #

    def build(self, selection: str, mode: str, is_ipvanish: bool = True) -> str:
        """
        Build conn.ovpn for `selection` (IPVanish country/city name).
        Returns the chosen source filename for display purposes.
        """
        self.filelist = []
        self._collect_files(selection, mode)

        if not self.filelist:
            raise FileNotFoundError(
                f"No config files found for selection: '{selection}'"
            )

        chosen = random.choice(self.filelist)
        source_path = IPVANISH_DIR / chosen
        self._write_conn_ovpn(source_path, is_ipvanish=is_ipvanish)
        return chosen

    def build_from_path(self, source_path: Path, is_ipvanish: bool) -> None:
        """Prepare conn.ovpn from an arbitrary .ovpn file path."""
        self._write_conn_ovpn(source_path, is_ipvanish=is_ipvanish)

    # ──── PRIVATE ──── #

    def _collect_files(self, selection: str, mode: str) -> None:
        all_files = [p.name for p in IPVANISH_DIR.glob("*.ovpn")]

        # Region groups (North America, Europe, etc.)
        if selection in region_map:
            keywords = region_map[selection]
            for f in all_files:
                if any(kw.lower().replace(" ", "-") in f.lower() for kw in keywords):
                    self.filelist.append(f)
            return

        if mode == "country":
            code = nations_dict.get(selection, "")
            if not code:
                return
            for f in all_files:
                if code in f and f.endswith(".ovpn"):
                    self.filelist.append(f)

        elif mode == "city":
            keyword = selection.lower().replace(" ", "-")
            for f in all_files:
                if keyword in f.lower() and f.endswith(".ovpn"):
                    self.filelist.append(f)

    def _write_conn_ovpn(self, source_path: Path, is_ipvanish: bool) -> None:
        dest_path  = CONFIGS_DIR / "conn.ovpn"
        creds_path = CONFIGS_DIR / "credentials"
        ca_path    = CONFIGS_DIR / "ca.ipvanish.com.crt"

        lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()

        has_redirect = any(
            "redirect-gateway" in l for l in lines
        )
        has_dns = any(
            "dhcp-option" in l and "DNS" in l for l in lines
        )

        with open(dest_path, "w") as out:
            for line in lines:
                stripped = line.strip()

                if stripped.startswith("auth-user-pass"):
                    parts = stripped.split()
                    # Only inject creds when: directive is bare AND this is an IPVanish profile.
                    # Third-party configs may embed credentials differently or not at all.
                    if len(parts) == 1 and is_ipvanish:
                        out.write(f"auth-user-pass {creds_path}\n\n")
                    else:
                        out.write(line + "\n")

                elif stripped.startswith("ca "):
                    # Rewrite only when the referenced cert doesn't exist next to the config.
                    # Configs with inline <ca>...</ca> blocks have no standalone ca directive.
                    ref = stripped[3:].strip()
                    ref_path = source_path.parent / ref
                    if not ref_path.exists() and ca_path.exists():
                        out.write(f"ca {ca_path}\n\n")
                    else:
                        out.write(line + "\n")

                elif "keysize 256" in stripped:
                    pass  # Deprecated OpenVPN directive — skip

                else:
                    out.write(line + "\n")

            # IPVanish profiles lack redirect-gateway / DNS directives — inject them.
            # Without these, traffic doesn't route through the tunnel and DNS isn't set.
            if is_ipvanish and not has_redirect:
                out.write("\nredirect-gateway def1 bypass-dhcp\n")
            if is_ipvanish and not has_dns:
                out.write("dhcp-option DNS 198.18.0.1\n")
                out.write("dhcp-option DNS 198.18.0.2\n")
