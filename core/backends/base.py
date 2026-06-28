"""
core/backends/base.py
Abstract base class for VPN protocol backends.
IPVanish-Client v2
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from core.profiles import Profile


class VPNBackend(ABC):
    """
    Protocol-agnostic interface for connect / disconnect / status.
    Each concrete backend manages its own process lifetime and
    interface detection; the ConnectionManager dispatches to the
    correct backend based on the active profile's protocol.
    """

    protocol: ClassVar[str]  # "openvpn" or "wireguard"

    @abstractmethod
    def connect(self, profile: "Profile") -> None:
        """Blocking — called from a QThread worker, never the GUI thread."""

    @abstractmethod
    def disconnect(self) -> None:
        """Blocking — called from a QThread worker."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Non-blocking — safe to call from any thread."""

    @abstractmethod
    def interface_name(self) -> str | None:
        """Return the active tunnel interface name, or None if not connected."""
