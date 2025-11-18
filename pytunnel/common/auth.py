"""Authentication and authorization system."""

import secrets
import hashlib
import hmac
import time
from typing import Dict, Optional, Set
from dataclasses import dataclass
import json


@dataclass
class User:
    """User account."""
    username: str
    password_hash: str
    api_key: str
    allowed_subdomains: Set[str]
    max_tunnels: int = 5
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class AuthManager:
    """Manages authentication and authorization."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, str] = {}  # api_key -> username
        self.active_tokens: Dict[str, tuple] = {}  # token -> (username, expiry)

    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def generate_api_key(self) -> str:
        """Generate a random API key."""
        return secrets.token_urlsafe(32)

    def generate_token(self, username: str, ttl: int = 3600) -> str:
        """Generate a temporary access token."""
        token = secrets.token_urlsafe(32)
        expiry = time.time() + ttl
        self.active_tokens[token] = (username, expiry)
        return token

    def create_user(
        self,
        username: str,
        password: str,
        allowed_subdomains: Optional[Set[str]] = None,
        max_tunnels: int = 5
    ) -> User:
        """Create a new user account."""
        if username in self.users:
            raise ValueError(f"User {username} already exists")

        password_hash = self.hash_password(password)
        api_key = self.generate_api_key()

        user = User(
            username=username,
            password_hash=password_hash,
            api_key=api_key,
            allowed_subdomains=allowed_subdomains or set(),
            max_tunnels=max_tunnels
        )

        self.users[username] = user
        self.api_keys[api_key] = username

        return user

    def verify_password(self, username: str, password: str) -> bool:
        """Verify username and password."""
        if username not in self.users:
            return False

        user = self.users[username]
        password_hash = self.hash_password(password)

        return hmac.compare_digest(user.password_hash, password_hash)

    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return username."""
        return self.api_keys.get(api_key)

    def verify_token(self, token: str) -> Optional[str]:
        """Verify token and return username."""
        if token not in self.active_tokens:
            return None

        username, expiry = self.active_tokens[token]

        # Check if token has expired
        if time.time() > expiry:
            del self.active_tokens[token]
            return None

        return username

    def revoke_token(self, token: str):
        """Revoke an access token."""
        if token in self.active_tokens:
            del self.active_tokens[token]

    def can_use_subdomain(self, username: str, subdomain: str) -> bool:
        """Check if user can use a specific subdomain."""
        if username not in self.users:
            return False

        user = self.users[username]

        # If no restrictions, allow any subdomain
        if not user.allowed_subdomains:
            return True

        # Check if subdomain matches any allowed pattern
        return subdomain in user.allowed_subdomains or '*' in user.allowed_subdomains

    def get_user_tunnel_count(self, username: str) -> int:
        """Get the number of active tunnels for a user."""
        # This will be implemented by the server
        return 0

    def can_create_tunnel(self, username: str) -> bool:
        """Check if user can create more tunnels."""
        if username not in self.users:
            return False

        user = self.users[username]
        current_count = self.get_user_tunnel_count(username)

        return current_count < user.max_tunnels

    def save_to_file(self, filename: str):
        """Save users to a JSON file."""
        data = {
            'users': {
                username: {
                    'password_hash': user.password_hash,
                    'api_key': user.api_key,
                    'allowed_subdomains': list(user.allowed_subdomains),
                    'max_tunnels': user.max_tunnels,
                    'created_at': user.created_at
                }
                for username, user in self.users.items()
            }
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filename: str):
        """Load users from a JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            for username, user_data in data.get('users', {}).items():
                user = User(
                    username=username,
                    password_hash=user_data['password_hash'],
                    api_key=user_data['api_key'],
                    allowed_subdomains=set(user_data.get('allowed_subdomains', [])),
                    max_tunnels=user_data.get('max_tunnels', 5),
                    created_at=user_data.get('created_at', time.time())
                )
                self.users[username] = user
                self.api_keys[user.api_key] = username

        except FileNotFoundError:
            # File doesn't exist yet, that's okay
            pass


# Global instance
_auth_manager = None


def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
