"""Tests for authentication and authorization."""

import pytest
from pytunnel.common.auth import AuthManager, User


def test_create_user():
    """Test creating a new user."""
    auth = AuthManager()
    user = auth.create_user("testuser", "password123")

    assert user.username == "testuser"
    assert user.api_key is not None
    assert user.password_hash != "password123"  # Should be hashed


def test_verify_password():
    """Test password verification."""
    auth = AuthManager()
    auth.create_user("testuser", "password123")

    assert auth.verify_password("testuser", "password123")
    assert not auth.verify_password("testuser", "wrongpassword")
    assert not auth.verify_password("nonexistent", "password123")


def test_verify_api_key():
    """Test API key verification."""
    auth = AuthManager()
    user = auth.create_user("testuser", "password123")

    assert auth.verify_api_key(user.api_key) == "testuser"
    assert auth.verify_api_key("invalid_key") is None


def test_generate_token():
    """Test token generation and verification."""
    auth = AuthManager()
    auth.create_user("testuser", "password123")

    token = auth.generate_token("testuser", ttl=3600)
    assert auth.verify_token(token) == "testuser"

    # Invalid token
    assert auth.verify_token("invalid_token") is None


def test_revoke_token():
    """Test token revocation."""
    auth = AuthManager()
    auth.create_user("testuser", "password123")

    token = auth.generate_token("testuser")
    assert auth.verify_token(token) == "testuser"

    auth.revoke_token(token)
    assert auth.verify_token(token) is None


def test_subdomain_permissions():
    """Test subdomain access permissions."""
    auth = AuthManager()
    auth.create_user("testuser", "password123", allowed_subdomains={"myapp", "test"})

    assert auth.can_use_subdomain("testuser", "myapp")
    assert auth.can_use_subdomain("testuser", "test")
    assert not auth.can_use_subdomain("testuser", "other")


def test_subdomain_wildcard():
    """Test wildcard subdomain permissions."""
    auth = AuthManager()
    auth.create_user("testuser", "password123", allowed_subdomains={"*"})

    assert auth.can_use_subdomain("testuser", "anything")
    assert auth.can_use_subdomain("testuser", "myapp")


def test_save_and_load_users():
    """Test saving and loading users from file."""
    import tempfile
    import os

    auth = AuthManager()
    auth.create_user("user1", "pass1", allowed_subdomains={"app1"})
    auth.create_user("user2", "pass2", max_tunnels=10)

    # Save to file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name

    try:
        auth.save_to_file(temp_file)

        # Load into new manager
        auth2 = AuthManager()
        auth2.load_from_file(temp_file)

        assert "user1" in auth2.users
        assert "user2" in auth2.users
        assert auth2.verify_password("user1", "pass1")
        assert auth2.users["user2"].max_tunnels == 10

    finally:
        os.unlink(temp_file)
