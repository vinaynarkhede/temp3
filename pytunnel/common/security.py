"""Advanced security features for PyTunnel."""

import time
import ipaddress
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from collections import deque
from enum import Enum


class SecurityPreset(Enum):
    """Security configuration presets."""
    BASIC = "basic"
    STANDARD = "standard"
    PARANOID = "paranoid"


@dataclass
class SecurityConfig:
    """Security configuration."""
    # IP filtering
    ip_whitelist: Set[str] = None
    ip_blacklist: Set[str] = None

    # Connection limits
    max_connections_per_ip: int = 10
    max_connections_total: int = 1000

    # DDoS protection
    connection_rate_limit: int = 100  # connections per minute
    request_rate_limit: int = 1000   # requests per minute
    enable_slowloris_protection: bool = True
    slow_request_timeout: int = 30   # seconds

    # Geographic restrictions
    allowed_countries: Optional[Set[str]] = None
    blocked_countries: Optional[Set[str]] = None

    # Request signature
    require_signature: bool = False
    signature_secret: Optional[str] = None

    def __post_init__(self):
        if self.ip_whitelist is None:
            self.ip_whitelist = set()
        if self.ip_blacklist is None:
            self.ip_blacklist = set()

    @classmethod
    def from_preset(cls, preset: SecurityPreset) -> 'SecurityConfig':
        """Create config from preset."""
        if preset == SecurityPreset.BASIC:
            return cls(
                max_connections_per_ip=50,
                connection_rate_limit=200,
                enable_slowloris_protection=False
            )
        elif preset == SecurityPreset.STANDARD:
            return cls(
                max_connections_per_ip=20,
                connection_rate_limit=100,
                request_rate_limit=1000,
                enable_slowloris_protection=True
            )
        elif preset == SecurityPreset.PARANOID:
            return cls(
                max_connections_per_ip=5,
                connection_rate_limit=50,
                request_rate_limit=500,
                enable_slowloris_protection=True,
                slow_request_timeout=15,
                require_signature=True
            )
        else:
            return cls()


class IPFilter:
    """IP address filtering with whitelist/blacklist support."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.whitelist_networks = self._parse_ip_list(config.ip_whitelist)
        self.blacklist_networks = self._parse_ip_list(config.ip_blacklist)

    def _parse_ip_list(self, ip_list: Set[str]) -> List:
        """Parse IP addresses/CIDR ranges."""
        networks = []
        for ip_str in ip_list:
            try:
                # Try as network (supports CIDR)
                network = ipaddress.ip_network(ip_str, strict=False)
                networks.append(network)
            except ValueError:
                # Try as individual IP
                try:
                    addr = ipaddress.ip_address(ip_str)
                    # Convert to /32 or /128 network
                    network = ipaddress.ip_network(f"{addr}/{addr.max_prefixlen}", strict=False)
                    networks.append(network)
                except ValueError:
                    pass  # Invalid IP, skip
        return networks

    def is_allowed(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """
        Check if IP address is allowed.

        Returns:
            Tuple of (allowed, reason)
        """
        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError:
            return False, "Invalid IP address"

        # Check blacklist first
        for network in self.blacklist_networks:
            if ip in network:
                return False, f"IP {ip_address} is blacklisted"

        # If whitelist is configured, IP must be in it
        if self.whitelist_networks:
            for network in self.whitelist_networks:
                if ip in network:
                    return True, None
            return False, f"IP {ip_address} not in whitelist"

        # No restrictions
        return True, None

    def add_to_whitelist(self, ip_or_network: str):
        """Add IP or network to whitelist."""
        self.config.ip_whitelist.add(ip_or_network)
        self.whitelist_networks = self._parse_ip_list(self.config.ip_whitelist)

    def add_to_blacklist(self, ip_or_network: str):
        """Add IP or network to blacklist."""
        self.config.ip_blacklist.add(ip_or_network)
        self.blacklist_networks = self._parse_ip_list(self.config.ip_blacklist)

    def remove_from_whitelist(self, ip_or_network: str):
        """Remove IP or network from whitelist."""
        self.config.ip_whitelist.discard(ip_or_network)
        self.whitelist_networks = self._parse_ip_list(self.config.ip_whitelist)

    def remove_from_blacklist(self, ip_or_network: str):
        """Remove IP or network from blacklist."""
        self.config.ip_blacklist.discard(ip_or_network)
        self.blacklist_networks = self._parse_ip_list(self.config.ip_blacklist)


class ConnectionTracker:
    """Tracks connections for rate limiting and DDoS protection."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.connections: Dict[str, int] = {}  # ip -> count
        self.connection_times: Dict[str, deque] = {}  # ip -> timestamps
        self.blocked_ips: Dict[str, float] = {}  # ip -> block_until
        self.total_connections = 0

    def can_connect(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """
        Check if IP can create a new connection.

        Returns:
            Tuple of (allowed, reason)
        """
        now = time.time()

        # Check if IP is temporarily blocked
        if ip_address in self.blocked_ips:
            if now < self.blocked_ips[ip_address]:
                remaining = int(self.blocked_ips[ip_address] - now)
                return False, f"IP blocked for {remaining} more seconds"
            else:
                # Unblock
                del self.blocked_ips[ip_address]

        # Check total connection limit
        if self.total_connections >= self.config.max_connections_total:
            return False, "Server at maximum capacity"

        # Check per-IP connection limit
        current_connections = self.connections.get(ip_address, 0)
        if current_connections >= self.config.max_connections_per_ip:
            return False, f"Too many connections from {ip_address}"

        # Check connection rate limit
        if ip_address in self.connection_times:
            # Clean old timestamps
            self.connection_times[ip_address] = deque([
                t for t in self.connection_times[ip_address]
                if now - t < 60  # Last minute
            ], maxlen=self.config.connection_rate_limit)

            # Check rate
            if len(self.connection_times[ip_address]) >= self.config.connection_rate_limit:
                # Block IP for 5 minutes
                self.blocked_ips[ip_address] = now + 300
                return False, "Connection rate limit exceeded - IP blocked"

        return True, None

    def register_connection(self, ip_address: str):
        """Register a new connection."""
        self.connections[ip_address] = self.connections.get(ip_address, 0) + 1
        self.total_connections += 1

        # Track connection time for rate limiting
        if ip_address not in self.connection_times:
            self.connection_times[ip_address] = deque(maxlen=self.config.connection_rate_limit)
        self.connection_times[ip_address].append(time.time())

    def unregister_connection(self, ip_address: str):
        """Unregister a connection."""
        if ip_address in self.connections:
            self.connections[ip_address] -= 1
            if self.connections[ip_address] <= 0:
                del self.connections[ip_address]

        self.total_connections = max(0, self.total_connections - 1)

    def get_connection_count(self, ip_address: str) -> int:
        """Get current connection count for IP."""
        return self.connections.get(ip_address, 0)

    def get_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            "total_connections": self.total_connections,
            "unique_ips": len(self.connections),
            "blocked_ips": len(self.blocked_ips),
            "max_connections_total": self.config.max_connections_total
        }


class DDoSProtection:
    """DDoS protection with automatic IP blocking."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.request_counts: Dict[str, deque] = {}  # ip -> timestamps
        self.suspicious_ips: Dict[str, int] = {}  # ip -> suspicion_score
        self.auto_blocked: Dict[str, float] = {}  # ip -> block_until

    def check_request_rate(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """
        Check if request rate is acceptable.

        Returns:
            Tuple of (allowed, reason)
        """
        now = time.time()

        # Check if auto-blocked
        if ip_address in self.auto_blocked:
            if now < self.auto_blocked[ip_address]:
                remaining = int(self.auto_blocked[ip_address] - now)
                return False, f"IP auto-blocked for {remaining} more seconds"
            else:
                del self.auto_blocked[ip_address]
                if ip_address in self.suspicious_ips:
                    del self.suspicious_ips[ip_address]

        # Track requests
        if ip_address not in self.request_counts:
            self.request_counts[ip_address] = deque(maxlen=self.config.request_rate_limit)

        # Clean old requests
        self.request_counts[ip_address] = deque([
            t for t in self.request_counts[ip_address]
            if now - t < 60  # Last minute
        ], maxlen=self.config.request_rate_limit)

        # Check rate
        current_rate = len(self.request_counts[ip_address])

        if current_rate >= self.config.request_rate_limit:
            # Increase suspicion score
            self.suspicious_ips[ip_address] = self.suspicious_ips.get(ip_address, 0) + 1

            # Auto-block after 3 violations
            if self.suspicious_ips[ip_address] >= 3:
                # Block for 1 hour
                self.auto_blocked[ip_address] = now + 3600
                return False, "Request rate limit exceeded - IP auto-blocked"

            return False, "Request rate limit exceeded"

        # Register request
        self.request_counts[ip_address].append(now)
        return True, None

    def get_blocked_ips(self) -> List[Dict]:
        """Get list of auto-blocked IPs."""
        now = time.time()
        blocked = []

        for ip, block_until in list(self.auto_blocked.items()):
            if now < block_until:
                blocked.append({
                    "ip": ip,
                    "blocked_until": block_until,
                    "remaining_seconds": int(block_until - now),
                    "suspicion_score": self.suspicious_ips.get(ip, 0)
                })
            else:
                # Clean up expired blocks
                del self.auto_blocked[ip]
                if ip in self.suspicious_ips:
                    del self.suspicious_ips[ip]

        return blocked

    def unblock_ip(self, ip_address: str):
        """Manually unblock an IP."""
        if ip_address in self.auto_blocked:
            del self.auto_blocked[ip_address]
        if ip_address in self.suspicious_ips:
            del self.suspicious_ips[ip_address]


class SecurityManager:
    """Unified security manager."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        if config is None:
            config = SecurityConfig.from_preset(SecurityPreset.STANDARD)

        self.config = config
        self.ip_filter = IPFilter(config)
        self.connection_tracker = ConnectionTracker(config)
        self.ddos_protection = DDoSProtection(config)

    def check_connection(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """
        Check if connection is allowed.

        Returns:
            Tuple of (allowed, reason)
        """
        # Check IP filter
        allowed, reason = self.ip_filter.is_allowed(ip_address)
        if not allowed:
            return False, reason

        # Check connection limits
        allowed, reason = self.connection_tracker.can_connect(ip_address)
        if not allowed:
            return False, reason

        return True, None

    def register_connection(self, ip_address: str):
        """Register a new connection."""
        self.connection_tracker.register_connection(ip_address)

    def unregister_connection(self, ip_address: str):
        """Unregister a connection."""
        self.connection_tracker.unregister_connection(ip_address)

    def check_request(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed (DDoS protection).

        Returns:
            Tuple of (allowed, reason)
        """
        return self.ddos_protection.check_request_rate(ip_address)

    def get_security_score(self) -> int:
        """
        Calculate security score (0-100).

        Higher is more secure.
        """
        score = 0

        # IP filtering (+20)
        if self.config.ip_whitelist or self.config.ip_blacklist:
            score += 20

        # Connection limits (+20)
        if self.config.max_connections_per_ip <= 10:
            score += 20

        # Rate limiting (+20)
        if self.config.connection_rate_limit <= 100:
            score += 20

        # DDoS protection (+20)
        if self.config.enable_slowloris_protection:
            score += 20

        # Request signature (+20)
        if self.config.require_signature:
            score += 20

        return score

    def get_stats(self) -> Dict:
        """Get comprehensive security statistics."""
        return {
            "security_score": self.get_security_score(),
            "connections": self.connection_tracker.get_stats(),
            "blocked_ips": self.ddos_protection.get_blocked_ips(),
            "config": {
                "max_connections_per_ip": self.config.max_connections_per_ip,
                "connection_rate_limit": self.config.connection_rate_limit,
                "request_rate_limit": self.config.request_rate_limit,
                "has_whitelist": bool(self.config.ip_whitelist),
                "has_blacklist": bool(self.config.ip_blacklist)
            }
        }


# Global instance
_security_manager = None


def get_security_manager(config: Optional[SecurityConfig] = None) -> SecurityManager:
    """Get the global security manager instance."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager(config)
    return _security_manager
