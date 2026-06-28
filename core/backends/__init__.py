"""core/backends — VPN protocol backend implementations."""

from core.backends.base import VPNBackend
from core.backends.openvpn_backend import OpenVPNBackend
from core.backends.wireguard_backend import WireGuardBackend

__all__ = ["VPNBackend", "OpenVPNBackend", "WireGuardBackend"]
