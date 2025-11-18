"""Subdomain management for custom tunnel URLs."""

import re
from typing import Dict, Optional, Set
from dataclasses import dataclass
import time


@dataclass
class SubdomainInfo:
    """Information about a registered subdomain."""
    subdomain: str
    client_id: str
    username: Optional[str]
    registered_at: float
    expires_at: Optional[float] = None

    def is_expired(self) -> bool:
        """Check if subdomain has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class SubdomainManager:
    """Manages subdomain assignments and reservations."""

    def __init__(self, base_domain: Optional[str] = None):
        self.base_domain = base_domain
        self.subdomains: Dict[str, SubdomainInfo] = {}  # subdomain -> info
        self.client_subdomains: Dict[str, str] = {}  # client_id -> subdomain
        self.reserved_subdomains: Set[str] = {
            'www', 'api', 'admin', 'dashboard', 'status',
            'tunnel', 'connect', 'ws', 'wss', 'https',
            'http', 'ftp', 'ssh', 'mail', 'smtp'
        }

    def is_valid_subdomain(self, subdomain: str) -> bool:
        """
        Check if subdomain is valid.

        Rules:
        - 3-63 characters
        - Lowercase letters, numbers, and hyphens only
        - Cannot start or end with hyphen
        - Cannot be reserved
        """
        if not subdomain or len(subdomain) < 3 or len(subdomain) > 63:
            return False

        if subdomain in self.reserved_subdomains:
            return False

        # Check pattern: lowercase alphanumeric and hyphens
        pattern = r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'
        return bool(re.match(pattern, subdomain))

    def is_available(self, subdomain: str) -> bool:
        """Check if subdomain is available."""
        if not self.is_valid_subdomain(subdomain):
            return False

        # Check if already registered
        if subdomain in self.subdomains:
            info = self.subdomains[subdomain]
            # If expired, it's available
            if info.is_expired():
                return True
            return False

        return True

    def register_subdomain(
        self,
        subdomain: str,
        client_id: str,
        username: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Register a subdomain for a client.

        Args:
            subdomain: Desired subdomain
            client_id: Client identifier
            username: Optional username for auth
            ttl: Time to live in seconds (None = permanent)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available(subdomain):
            return False

        # Remove expired subdomain if exists
        if subdomain in self.subdomains and self.subdomains[subdomain].is_expired():
            self._unregister_subdomain(subdomain)

        # Calculate expiry
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl

        # Register subdomain
        info = SubdomainInfo(
            subdomain=subdomain,
            client_id=client_id,
            username=username,
            registered_at=time.time(),
            expires_at=expires_at
        )

        self.subdomains[subdomain] = info
        self.client_subdomains[client_id] = subdomain

        return True

    def _unregister_subdomain(self, subdomain: str):
        """Internal method to unregister a subdomain."""
        if subdomain in self.subdomains:
            info = self.subdomains[subdomain]
            del self.subdomains[subdomain]
            if info.client_id in self.client_subdomains:
                del self.client_subdomains[info.client_id]

    def unregister_subdomain(self, subdomain: str, client_id: Optional[str] = None) -> bool:
        """
        Unregister a subdomain.

        Args:
            subdomain: Subdomain to unregister
            client_id: Optional client ID for verification

        Returns:
            True if successful, False otherwise
        """
        if subdomain not in self.subdomains:
            return False

        info = self.subdomains[subdomain]

        # If client_id provided, verify ownership
        if client_id and info.client_id != client_id:
            return False

        self._unregister_subdomain(subdomain)
        return True

    def unregister_client(self, client_id: str):
        """Unregister all subdomains for a client."""
        if client_id in self.client_subdomains:
            subdomain = self.client_subdomains[client_id]
            self._unregister_subdomain(subdomain)

    def get_client_for_subdomain(self, subdomain: str) -> Optional[str]:
        """Get client ID for a subdomain."""
        if subdomain not in self.subdomains:
            return None

        info = self.subdomains[subdomain]

        # Check if expired
        if info.is_expired():
            self._unregister_subdomain(subdomain)
            return None

        return info.client_id

    def get_subdomain_for_client(self, client_id: str) -> Optional[str]:
        """Get subdomain for a client."""
        return self.client_subdomains.get(client_id)

    def get_full_domain(self, subdomain: str) -> str:
        """Get full domain name for subdomain."""
        if self.base_domain:
            return f"{subdomain}.{self.base_domain}"
        return subdomain

    def cleanup_expired(self) -> int:
        """Remove expired subdomains. Returns number removed."""
        expired = [
            subdomain
            for subdomain, info in self.subdomains.items()
            if info.is_expired()
        ]

        for subdomain in expired:
            self._unregister_subdomain(subdomain)

        return len(expired)

    def reserve_subdomain(self, subdomain: str):
        """Add subdomain to reserved list."""
        self.reserved_subdomains.add(subdomain.lower())

    def unreserve_subdomain(self, subdomain: str):
        """Remove subdomain from reserved list."""
        self.reserved_subdomains.discard(subdomain.lower())

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about subdomains."""
        total = len(self.subdomains)
        expired = sum(1 for info in self.subdomains.values() if info.is_expired())
        active = total - expired

        return {
            'total': total,
            'active': active,
            'expired': expired,
            'reserved': len(self.reserved_subdomains)
        }


# Global instance
_subdomain_manager = None


def get_subdomain_manager(base_domain: Optional[str] = None) -> SubdomainManager:
    """Get the global subdomain manager instance."""
    global _subdomain_manager
    if _subdomain_manager is None:
        _subdomain_manager = SubdomainManager(base_domain)
    return _subdomain_manager
