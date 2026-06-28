"""
tests/test_backends.py
Pure-function tests for core/backends/openvpn_backend.py and core/config_parser.py.
No GUI, no pkexec, no network, no subprocess required.
IPVanish-Client v2
"""

from pathlib import Path

from core.backends.openvpn_backend import _parse_dev
from core.config_parser import ConfigParser


# ──── _parse_dev ──── #

def test_openvpn_dev_parsed_from_ovpn(tmp_path):
    ovpn = tmp_path / "test.ovpn"
    ovpn.write_text("client\nremote example.com 1194\ndev tun1\n")
    assert _parse_dev(ovpn) == "tun1"


def test_openvpn_dev_tun_no_suffix_gets_zero(tmp_path):
    """'dev tun' (no digit) → append '0'."""
    ovpn = tmp_path / "test.ovpn"
    ovpn.write_text("client\ndev tun\n")
    assert _parse_dev(ovpn) == "tun0"


def test_openvpn_dev_fallback_tun0(tmp_path):
    """No dev directive at all → fallback 'tun0'."""
    ovpn = tmp_path / "test.ovpn"
    ovpn.write_text("client\nremote example.com 1194\n")
    assert _parse_dev(ovpn) == "tun0"


def test_openvpn_dev_missing_file():
    """Non-existent file → fallback 'tun0' (no exception)."""
    assert _parse_dev(Path("/tmp/nonexistent_abc123.ovpn")) == "tun0"


def test_openvpn_dev_tap_device(tmp_path):
    """tap devices are parsed correctly."""
    ovpn = tmp_path / "test.ovpn"
    ovpn.write_text("dev tap0\n")
    assert _parse_dev(ovpn) == "tap0"


# ──── ConfigParser — ca rewrite ──── #

def _make_ca_cert(tmp_path: Path) -> Path:
    ca = tmp_path / "ca.ipvanish.com.crt"
    ca.write_text("-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n")
    return ca


def test_config_ca_rewrite_when_file_missing(tmp_path):
    """ca directive rewritten when referenced cert doesn't exist beside the config."""
    # Source lives in a subdirectory; cert lives only in config dir (tmp_path)
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    source = profile_dir / "ipvanish-SG-a01.ovpn"
    source.write_text("client\nca ca.ipvanish.com.crt\nremote example.com 1194\n")

    ca_cert = _make_ca_cert(tmp_path)  # in config dir, NOT beside source
    conn = tmp_path / "conn.ovpn"

    import core.config_parser as _mod
    orig_configs = _mod.CONFIGS_DIR
    _mod.CONFIGS_DIR = tmp_path
    try:
        parser = ConfigParser()
        parser.build_from_path(source, is_ipvanish=True)
        content = conn.read_text()
        assert str(ca_cert) in content, "Expected ca path rewritten to absolute cert path"
    finally:
        _mod.CONFIGS_DIR = orig_configs


def test_config_ca_no_rewrite_when_adjacent(tmp_path):
    """ca directive left alone when referenced cert exists next to the config file."""
    source_dir = tmp_path / "profiles"
    source_dir.mkdir()
    # Place the cert beside the source config
    (source_dir / "ca.ipvanish.com.crt").write_text("-----BEGIN CERTIFICATE-----\n")
    source = source_dir / "test.ovpn"
    source.write_text("client\nca ca.ipvanish.com.crt\nremote example.com 1194\n")

    conn = tmp_path / "conn.ovpn"

    import core.config_parser as _mod
    orig_configs = _mod.CONFIGS_DIR
    _mod.CONFIGS_DIR = tmp_path
    try:
        parser = ConfigParser()
        parser.build_from_path(source, is_ipvanish=True)
        content = conn.read_text()
        # Original line preserved (cert is present beside config)
        assert "ca ca.ipvanish.com.crt" in content
    finally:
        _mod.CONFIGS_DIR = orig_configs


def test_config_ca_no_rewrite_when_inline(tmp_path):
    """Config with inline <ca> block has no ca directive — nothing rewritten."""
    source = tmp_path / "test.ovpn"
    source.write_text(
        "client\nremote example.com 1194\n<ca>\n-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n</ca>\n"
    )
    conn = tmp_path / "conn.ovpn"

    import core.config_parser as _mod
    orig_configs = _mod.CONFIGS_DIR
    _mod.CONFIGS_DIR = tmp_path
    try:
        parser = ConfigParser()
        parser.build_from_path(source, is_ipvanish=True)
        content = conn.read_text()
        # No standalone ca directive present → no rewrite
        assert "ca " not in content.splitlines()[0]
        assert "<ca>" in content
    finally:
        _mod.CONFIGS_DIR = orig_configs


# ──── ConfigParser — auth-user-pass rewrite ──── #

def _make_credentials(tmp_path: Path) -> Path:
    creds = tmp_path / "credentials"
    creds.write_text("user@example.com\npassword123\n")
    return creds


def test_config_authpass_rewrite_bare_ipvanish(tmp_path):
    """Bare auth-user-pass + is_ipvanish=True → injected with credentials path."""
    source = tmp_path / "ipvanish-US-a01.ovpn"
    source.write_text("client\nremote example.com 1194\nauth-user-pass\n")

    creds = _make_credentials(tmp_path)
    conn = tmp_path / "conn.ovpn"

    import core.config_parser as _mod
    orig_configs = _mod.CONFIGS_DIR
    _mod.CONFIGS_DIR = tmp_path
    try:
        parser = ConfigParser()
        parser.build_from_path(source, is_ipvanish=True)
        content = conn.read_text()
        assert f"auth-user-pass {creds}" in content
    finally:
        _mod.CONFIGS_DIR = orig_configs


def test_config_authpass_no_rewrite_third_party(tmp_path):
    """Bare auth-user-pass + is_ipvanish=False → left unchanged."""
    source = tmp_path / "third-party.ovpn"
    source.write_text("client\nremote example.com 1194\nauth-user-pass\n")

    _make_credentials(tmp_path)
    conn = tmp_path / "conn.ovpn"

    import core.config_parser as _mod
    orig_configs = _mod.CONFIGS_DIR
    _mod.CONFIGS_DIR = tmp_path
    try:
        parser = ConfigParser()
        parser.build_from_path(source, is_ipvanish=False)
        content = conn.read_text()
        # Should remain as bare directive, not injected
        assert "auth-user-pass\n" in content
        assert "credentials" not in content
    finally:
        _mod.CONFIGS_DIR = orig_configs


def test_config_authpass_with_arg_not_rewritten(tmp_path):
    """auth-user-pass /some/path (already has arg) → preserved as-is even for IPVanish."""
    source = tmp_path / "test.ovpn"
    source.write_text("client\nauth-user-pass /some/existing/creds\nremote example.com 1194\n")

    _make_credentials(tmp_path)
    conn = tmp_path / "conn.ovpn"

    import core.config_parser as _mod
    orig_configs = _mod.CONFIGS_DIR
    _mod.CONFIGS_DIR = tmp_path
    try:
        parser = ConfigParser()
        parser.build_from_path(source, is_ipvanish=True)
        content = conn.read_text()
        assert "auth-user-pass /some/existing/creds" in content
    finally:
        _mod.CONFIGS_DIR = orig_configs


# ──── ConfigParser — keysize skip ──── #

def test_config_keysize_256_stripped(tmp_path):
    """Deprecated keysize 256 directive omitted from output."""
    source = tmp_path / "test.ovpn"
    source.write_text("client\nkeysize 256\nremote example.com 1194\n")

    conn = tmp_path / "conn.ovpn"

    import core.config_parser as _mod
    orig_configs = _mod.CONFIGS_DIR
    _mod.CONFIGS_DIR = tmp_path
    try:
        parser = ConfigParser()
        parser.build_from_path(source, is_ipvanish=False)
        content = conn.read_text()
        assert "keysize" not in content
    finally:
        _mod.CONFIGS_DIR = orig_configs
