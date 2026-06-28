import pytest
import sys
sys.path.insert(0, '/home/blackflame/.local/bin')


def test_parse_tun0_returns_rx_tx():
    """_parse_tun0 returns (rx_bytes, tx_bytes) tuple from /proc/net/dev format."""
    sample = (
        "Inter-|   Receive                                                |  Transmit\n"
        " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
        "  tun0: 1024000     1000    0    0    0     0          0         0  512000     500    0    0    0     0       0          0\n"
    )
    from ipvanish_widget_daemon import _parse_tun0
    result = _parse_tun0(sample)
    assert result == (1024000, 512000)


def test_parse_tun0_returns_none_when_missing():
    from ipvanish_widget_daemon import _parse_tun0
    result = _parse_tun0("  eth0: 1024 0 0 0 0 0 0 0 512 0 0 0 0 0 0 0\n")
    assert result is None


def test_parse_ovpn_path_city_country():
    from ipvanish_widget_daemon import _parse_ovpn_location
    loc, host = _parse_ovpn_location(
        '/home/blackflame/vpn/ipvanish/ipvanish-SG-Singapore-sin-a02.ovpn'
    )
    assert loc == 'Singapore, SG'
    assert host == 'sin-a02.ipvanish.com'


def test_parse_ovpn_path_multiword_city():
    from ipvanish_widget_daemon import _parse_ovpn_location
    loc, host = _parse_ovpn_location(
        '/home/blackflame/vpn/ipvanish/ipvanish-US-Los-Angeles-lax-b01.ovpn'
    )
    assert loc == 'Los Angeles, US'
    assert host == 'lax-b01.ipvanish.com'


def test_parse_ovpn_path_not_connected():
    from ipvanish_widget_daemon import _parse_ovpn_location
    loc, host = _parse_ovpn_location(None)
    assert loc == 'Not connected'
    assert host == ''


def test_normalise_history_empty():
    from ipvanish_widget_daemon import _normalise
    result = _normalise([0.0] * 20)
    assert all(v == 0.01 for v in result)


def test_normalise_history_scales_to_max():
    from ipvanish_widget_daemon import _normalise
    data = [0.0] * 19 + [1000.0]
    result = _normalise(data)
    assert result[-1] == pytest.approx(1.0)
    assert result[0] == pytest.approx(0.01)


def test_format_bps_bytes():
    from ipvanish_widget_daemon import _fmt_bps
    assert _fmt_bps(500.0, bits=False) == '500 B/s'
    assert _fmt_bps(2048.0, bits=False) == '2.0 KB/s'
    assert _fmt_bps(2097152.0, bits=False) == '2.0 MB/s'


def test_format_bps_bits():
    from ipvanish_widget_daemon import _fmt_bps
    assert _fmt_bps(62500.0, bits=True) == '500.0 kb/s'   # 62500 * 8 = 500000 b/s = 500 kb/s
    assert _fmt_bps(1250000.0, bits=True) == '10.0 Mb/s'  # 1250000 * 8 = 10000000 b/s = 10 Mb/s
