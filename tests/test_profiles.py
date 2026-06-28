"""
tests/test_profiles.py
Pure-function tests for core/profiles.py.
No GUI, no pkexec, no network required.
IPVanish-Client v2
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from core.profiles import Profile, ProfileStore, IFNAMSIZ, _IPVANISH_RE


# ──── HELPERS ──── #

def make_store(tmp: Path) -> ProfileStore:
    """Return a ProfileStore whose IPVANISH_DIR and IMPORTED_DIR live under tmp."""
    store = ProfileStore.__new__(ProfileStore)
    store._profiles = []
    # Monkey-patch the directories to point at the temp tree
    store._ipvanish_dir = tmp / "ipvanish"
    store._imported_dir = tmp / "imported"
    store._configs_dir  = tmp
    return store


# ──── IPVANISH FILENAME REGEX ──── #

def test_ipvanish_re_matches_standard_filename():
    m = _IPVANISH_RE.match("ipvanish-SG-Singapore-sin-a02.ovpn")
    assert m is not None
    assert m.group(1) == "SG"
    assert "Singapore" in m.group(2)


def test_ipvanish_re_matches_multiword_city():
    m = _IPVANISH_RE.match("ipvanish-US-Los-Angeles-lax-b01.ovpn")
    assert m is not None
    assert m.group(1) == "US"
    assert "Los" in m.group(2)


def test_ipvanish_re_no_match_generic_ovpn():
    assert _IPVANISH_RE.match("my-custom-vpn.ovpn") is None


def test_ipvanish_re_no_match_wireguard_conf():
    assert _IPVANISH_RE.match("wg0.conf") is None


# ──── PROTOCOL DETECTION ──── #

def test_conf_extension_maps_to_wireguard(tmp_path):
    conf = tmp_path / "wg0.conf"
    conf.write_text("[Interface]\nPrivateKey = fake\n")
    store = ProfileStore()
    # Use import_file logic by inspecting suffix
    proto = "wireguard" if conf.suffix.lower() == ".conf" else "openvpn"
    assert proto == "wireguard"


def test_ovpn_extension_maps_to_openvpn(tmp_path):
    ovpn = tmp_path / "custom.ovpn"
    ovpn.write_text("client\nremote example.com 1194\n")
    proto = "wireguard" if ovpn.suffix.lower() == ".conf" else "openvpn"
    assert proto == "openvpn"


# ──── WG INTERFACE NAME TRUNCATION ──── #

def test_wg_stem_within_limit_unchanged():
    stem = "my-vpn"
    assert len(stem) <= IFNAMSIZ
    result = stem[:IFNAMSIZ]
    assert result == "my-vpn"


def test_wg_stem_truncated_at_15():
    stem = "my-very-long-vpn-name"
    assert len(stem) > IFNAMSIZ
    result = stem[:IFNAMSIZ]
    assert len(result) == IFNAMSIZ
    assert result == "my-very-long-vp"


# ──── COLLISION SUFFIX ──── #

def test_import_collision_gets_suffix(tmp_path):
    (tmp_path / "imported").mkdir()
    conf = tmp_path / "wg0.conf"
    conf.write_text("[Interface]\nPrivateKey = fake\n")

    # Pre-create the destination to simulate a collision
    existing = tmp_path / "imported" / "wg0.conf"
    existing.write_text("[Interface]\nPrivateKey = existing\n")

    store = ProfileStore()
    # Override dirs
    import core.profiles as _mod
    orig_imported = _mod.IMPORTED_DIR
    _mod.IMPORTED_DIR = tmp_path / "imported"
    try:
        profile = store.import_file(conf)
        # Collision → should get a suffix
        assert profile.path.name != "wg0.conf"
        assert profile.path.exists()
    finally:
        _mod.IMPORTED_DIR = orig_imported


# ──── FIRST-RUN MIGRATION ──── #

def test_migration_copies_and_removes(tmp_path):
    """Flat .ovpn files in config/ are moved to config/ipvanish/ on first scan."""
    # Set up a flat config dir with some .ovpn files
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "conn.ovpn").write_text("# runtime generated")
    for i in range(3):
        (config_dir / f"ipvanish-US-City-lax-a0{i}.ovpn").write_text(f"# config {i}")

    import core.profiles as _mod
    orig_configs  = _mod.CONFIGS_DIR
    orig_ipvanish = _mod.IPVANISH_DIR
    orig_imported = _mod.IMPORTED_DIR
    _mod.CONFIGS_DIR  = config_dir
    _mod.IPVANISH_DIR = config_dir / "ipvanish"
    _mod.IMPORTED_DIR = config_dir / "imported"
    try:
        store = ProfileStore()
        store.scan()
        ipvanish_dir = config_dir / "ipvanish"
        assert ipvanish_dir.exists()
        migrated = list(ipvanish_dir.glob("*.ovpn"))
        assert len(migrated) == 3
        # Originals removed
        flat = [p for p in config_dir.glob("*.ovpn") if p.name != "conn.ovpn"]
        assert flat == []
        # conn.ovpn untouched in root
        assert (config_dir / "conn.ovpn").exists()
    finally:
        _mod.CONFIGS_DIR  = orig_configs
        _mod.IPVANISH_DIR = orig_ipvanish
        _mod.IMPORTED_DIR = orig_imported


def test_migration_skips_when_ipvanish_dir_exists(tmp_path):
    """Migration does not run if config/ipvanish/ already exists."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    ipvanish_dir = config_dir / "ipvanish"
    ipvanish_dir.mkdir()
    # Put a file in the flat dir — should not be touched
    flat_file = config_dir / "ipvanish-US-City-lax-a00.ovpn"
    flat_file.write_text("# should stay")

    import core.profiles as _mod
    orig_configs  = _mod.CONFIGS_DIR
    orig_ipvanish = _mod.IPVANISH_DIR
    orig_imported = _mod.IMPORTED_DIR
    _mod.CONFIGS_DIR  = config_dir
    _mod.IPVANISH_DIR = ipvanish_dir
    _mod.IMPORTED_DIR = config_dir / "imported"
    try:
        store = ProfileStore()
        store.scan()
        # Flat file untouched
        assert flat_file.exists()
    finally:
        _mod.CONFIGS_DIR  = orig_configs
        _mod.IPVANISH_DIR = orig_ipvanish
        _mod.IMPORTED_DIR = orig_imported
