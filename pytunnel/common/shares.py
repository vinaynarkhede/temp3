"""Shareable tunnel links with time-limited access."""

import time
import hashlib
import secrets
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import json


@dataclass
class ShareLink:
    """Represents a shareable tunnel link."""
    share_id: str
    tunnel_id: str
    created_by: Optional[str]
    created_at: float
    expires_at: float
    password_hash: Optional[str]
    access_count: int = 0
    last_accessed: Optional[float] = None
    ip_whitelist: Optional[List[str]] = None
    max_access_count: Optional[int] = None
    revoked: bool = False

    def is_expired(self) -> bool:
        """Check if share link has expired."""
        if self.revoked:
            return True
        return time.time() > self.expires_at

    def is_access_exceeded(self) -> bool:
        """Check if access count exceeded."""
        if self.max_access_count is None:
            return False
        return self.access_count >= self.max_access_count

    def can_access(self, ip_address: Optional[str] = None) -> bool:
        """Check if access is allowed."""
        if self.is_expired():
            return False
        if self.is_access_exceeded():
            return False
        if self.ip_whitelist and ip_address:
            return ip_address in self.ip_whitelist
        return True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class ShareManager:
    """Manages shareable tunnel links."""

    def __init__(self):
        self.shares: Dict[str, ShareLink] = {}
        self.failed_attempts: Dict[str, List[float]] = {}  # share_id -> [timestamps]
        self.lockouts: Dict[str, float] = {}  # share_id -> lockout_until

    def generate_share_id(self, length: int = 8) -> str:
        """Generate a short, memorable share ID."""
        # Use URL-safe characters
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(secrets.choice(chars) for _ in range(length))

    def generate_password(self) -> str:
        """Generate a memorable password using word combinations."""
        # Simple word list for memorable passwords
        adjectives = ['happy', 'swift', 'brave', 'calm', 'bright', 'clever', 'gentle']
        nouns = ['tiger', 'river', 'mountain', 'forest', 'ocean', 'star', 'moon']
        numbers = str(secrets.randbelow(1000)).zfill(3)

        return f"{secrets.choice(adjectives)}-{secrets.choice(nouns)}-{numbers}"

    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def create_share(
        self,
        tunnel_id: str,
        expires_in_seconds: int = 86400,  # 24 hours default
        password: Optional[str] = None,
        created_by: Optional[str] = None,
        ip_whitelist: Optional[List[str]] = None,
        max_access_count: Optional[int] = None
    ) -> tuple[ShareLink, Optional[str]]:
        """
        Create a new share link.

        Args:
            tunnel_id: ID of the tunnel to share
            expires_in_seconds: Expiration time in seconds (max 7 days)
            password: Optional password (will be generated if None)
            created_by: Username who created the share
            ip_whitelist: Optional list of allowed IP addresses
            max_access_count: Optional maximum number of accesses

        Returns:
            Tuple of (ShareLink, plain_password or None)
        """
        # Enforce maximum expiration of 7 days
        max_expiry = 7 * 24 * 3600  # 7 days
        if expires_in_seconds > max_expiry:
            expires_in_seconds = max_expiry

        # Generate share ID
        share_id = self.generate_share_id()
        while share_id in self.shares:
            share_id = self.generate_share_id()

        # Handle password
        plain_password = None
        password_hash = None
        if password:
            password_hash = self.hash_password(password)
        elif password is False:
            # Explicitly no password
            pass
        else:
            # Generate password
            plain_password = self.generate_password()
            password_hash = self.hash_password(plain_password)

        # Create share
        share = ShareLink(
            share_id=share_id,
            tunnel_id=tunnel_id,
            created_by=created_by,
            created_at=time.time(),
            expires_at=time.time() + expires_in_seconds,
            password_hash=password_hash,
            ip_whitelist=ip_whitelist,
            max_access_count=max_access_count
        )

        self.shares[share_id] = share
        return share, plain_password

    def verify_password(self, share_id: str, password: str) -> bool:
        """Verify password for a share."""
        if share_id not in self.shares:
            return False

        share = self.shares[share_id]

        # No password required
        if not share.password_hash:
            return True

        # Check for lockout
        if self._is_locked_out(share_id):
            return False

        # Verify password
        password_hash = self.hash_password(password)
        if password_hash == share.password_hash:
            # Clear failed attempts on success
            if share_id in self.failed_attempts:
                del self.failed_attempts[share_id]
            return True

        # Record failed attempt
        self._record_failed_attempt(share_id)
        return False

    def _is_locked_out(self, share_id: str) -> bool:
        """Check if share is locked out due to failed attempts."""
        if share_id in self.lockouts:
            if time.time() < self.lockouts[share_id]:
                return True
            else:
                # Lockout expired
                del self.lockouts[share_id]
        return False

    def _record_failed_attempt(self, share_id: str):
        """Record a failed password attempt."""
        now = time.time()

        if share_id not in self.failed_attempts:
            self.failed_attempts[share_id] = []

        # Clean up old attempts (older than 15 minutes)
        self.failed_attempts[share_id] = [
            t for t in self.failed_attempts[share_id]
            if now - t < 900  # 15 minutes
        ]

        # Add new attempt
        self.failed_attempts[share_id].append(now)

        # Check if should lockout (3 attempts in 15 minutes)
        if len(self.failed_attempts[share_id]) >= 3:
            # Lockout for 15 minutes
            self.lockouts[share_id] = now + 900

    def get_share(self, share_id: str) -> Optional[ShareLink]:
        """Get a share by ID."""
        return self.shares.get(share_id)

    def access_share(
        self,
        share_id: str,
        password: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Attempt to access a share.

        Returns:
            Tuple of (success, error_message)
        """
        if share_id not in self.shares:
            return False, "Share not found"

        share = self.shares[share_id]

        # Check if share can be accessed
        if not share.can_access(ip_address):
            if share.is_expired():
                return False, "Share has expired"
            if share.is_access_exceeded():
                return False, "Access limit exceeded"
            if share.ip_whitelist and ip_address:
                return False, "IP address not allowed"
            return False, "Access denied"

        # Check lockout
        if self._is_locked_out(share_id):
            return False, "Too many failed attempts. Please try again later."

        # Verify password if required
        if share.password_hash:
            if not password:
                return False, "Password required"
            if not self.verify_password(share_id, password):
                return False, "Invalid password"

        # Record access
        share.access_count += 1
        share.last_accessed = time.time()

        return True, None

    def revoke_share(self, share_id: str) -> bool:
        """Revoke a share link."""
        if share_id not in self.shares:
            return False

        self.shares[share_id].revoked = True
        return True

    def cleanup_expired(self) -> int:
        """Remove expired shares. Returns count removed."""
        expired = [
            share_id
            for share_id, share in self.shares.items()
            if share.is_expired()
        ]

        for share_id in expired:
            del self.shares[share_id]

        return len(expired)

    def get_shares_for_tunnel(self, tunnel_id: str) -> List[ShareLink]:
        """Get all shares for a tunnel."""
        return [
            share for share in self.shares.values()
            if share.tunnel_id == tunnel_id
        ]

    def get_stats(self, share_id: str) -> Optional[Dict]:
        """Get statistics for a share."""
        if share_id not in self.shares:
            return None

        share = self.shares[share_id]
        now = time.time()

        return {
            'share_id': share.share_id,
            'access_count': share.access_count,
            'max_access_count': share.max_access_count,
            'created_at': share.created_at,
            'expires_at': share.expires_at,
            'last_accessed': share.last_accessed,
            'time_remaining': max(0, share.expires_at - now),
            'is_expired': share.is_expired(),
            'is_revoked': share.revoked,
            'has_password': share.password_hash is not None,
            'has_ip_whitelist': share.ip_whitelist is not None
        }

    def save_to_file(self, filename: str):
        """Save shares to a JSON file."""
        data = {
            'shares': {
                share_id: share.to_dict()
                for share_id, share in self.shares.items()
            }
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filename: str):
        """Load shares from a JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            for share_id, share_data in data.get('shares', {}).items():
                share = ShareLink(**share_data)
                self.shares[share_id] = share

        except FileNotFoundError:
            # File doesn't exist yet
            pass


# Global instance
_share_manager = None


def get_share_manager() -> ShareManager:
    """Get the global share manager instance."""
    global _share_manager
    if _share_manager is None:
        _share_manager = ShareManager()
    return _share_manager
