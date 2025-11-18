"""Tests for shareable tunnel links."""

import pytest
import time
from pytunnel.common.shares import ShareManager, ShareLink


def test_generate_share_id():
    """Test share ID generation."""
    manager = ShareManager()
    share_id = manager.generate_share_id()

    assert len(share_id) == 8
    assert share_id.isalnum()
    assert share_id.islower()


def test_generate_password():
    """Test password generation."""
    manager = ShareManager()
    password = manager.generate_password()

    # Format: word-word-123
    parts = password.split('-')
    assert len(parts) == 3
    assert parts[0].isalpha()
    assert parts[1].isalpha()
    assert parts[2].isdigit()
    assert len(parts[2]) == 3


def test_create_share():
    """Test creating a share."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123",
        expires_in_seconds=3600,
        created_by="user@example.com"
    )

    assert share.tunnel_id == "tunnel123"
    assert share.created_by == "user@example.com"
    assert password is not None  # Auto-generated
    assert share.password_hash is not None
    assert not share.is_expired()


def test_create_share_without_password():
    """Test creating share without password."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123",
        password=False  # Explicitly no password
    )

    assert share.password_hash is None
    assert password is None


def test_create_share_with_custom_password():
    """Test creating share with custom password."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123",
        password="my-secret-password"
    )

    assert share.password_hash is not None
    assert password is None  # Not returned for custom password
    assert manager.verify_password(share.share_id, "my-secret-password")


def test_max_expiry():
    """Test maximum expiry enforcement."""
    manager = ShareManager()

    # Try to create share with 10 days expiry (max is 7)
    share, _ = manager.create_share(
        tunnel_id="tunnel123",
        expires_in_seconds=10 * 24 * 3600  # 10 days
    )

    # Should be capped at 7 days
    max_expiry = 7 * 24 * 3600
    assert share.expires_at <= share.created_at + max_expiry + 1


def test_password_verification():
    """Test password verification."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123"
    )

    # Correct password
    assert manager.verify_password(share.share_id, password)

    # Wrong password
    assert not manager.verify_password(share.share_id, "wrong-password")


def test_lockout_after_failed_attempts():
    """Test lockout after multiple failed attempts."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123"
    )

    # 3 failed attempts
    for _ in range(3):
        manager.verify_password(share.share_id, "wrong")

    # Should be locked out
    assert manager._is_locked_out(share.share_id)

    # Even correct password should fail when locked out
    assert not manager.verify_password(share.share_id, password)


def test_access_share():
    """Test accessing a share."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123"
    )

    # Access with correct password
    success, error = manager.access_share(
        share.share_id,
        password=password
    )

    assert success
    assert error is None
    assert share.access_count == 1


def test_access_share_without_password():
    """Test accessing share without password protection."""
    manager = ShareManager()

    share, _ = manager.create_share(
        tunnel_id="tunnel123",
        password=False
    )

    # Access without password
    success, error = manager.access_share(share.share_id)

    assert success
    assert error is None


def test_access_expired_share():
    """Test accessing expired share."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123",
        expires_in_seconds=1  # 1 second
    )

    # Wait for expiration
    time.sleep(1.1)

    # Try to access
    success, error = manager.access_share(share.share_id, password=password)

    assert not success
    assert "expired" in error.lower()


def test_access_with_max_count():
    """Test max access count enforcement."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123",
        max_access_count=2
    )

    # First two accesses should succeed
    manager.access_share(share.share_id, password=password)
    manager.access_share(share.share_id, password=password)

    # Third should fail
    success, error = manager.access_share(share.share_id, password=password)

    assert not success
    assert "limit" in error.lower()


def test_ip_whitelist():
    """Test IP whitelist enforcement."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123",
        ip_whitelist=["192.168.1.1"]
    )

    # Allowed IP
    success, _ = manager.access_share(
        share.share_id,
        password=password,
        ip_address="192.168.1.1"
    )
    assert success

    # Not allowed IP
    success, error = manager.access_share(
        share.share_id,
        password=password,
        ip_address="192.168.1.2"
    )
    assert not success
    assert "not allowed" in error.lower()


def test_revoke_share():
    """Test revoking a share."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123"
    )

    # Revoke
    assert manager.revoke_share(share.share_id)

    # Try to access
    success, error = manager.access_share(share.share_id, password=password)

    assert not success


def test_get_share_stats():
    """Test getting share statistics."""
    manager = ShareManager()

    share, password = manager.create_share(
        tunnel_id="tunnel123",
        expires_in_seconds=3600
    )

    # Access once
    manager.access_share(share.share_id, password=password)

    # Get stats
    stats = manager.get_stats(share.share_id)

    assert stats['access_count'] == 1
    assert not stats['is_expired']
    assert stats['has_password']
    assert stats['time_remaining'] > 0


def test_cleanup_expired():
    """Test cleanup of expired shares."""
    manager = ShareManager()

    # Create expired share
    share1, _ = manager.create_share(
        tunnel_id="tunnel1",
        expires_in_seconds=1
    )

    # Create active share
    share2, _ = manager.create_share(
        tunnel_id="tunnel2",
        expires_in_seconds=3600
    )

    # Wait for expiration
    time.sleep(1.1)

    # Cleanup
    removed = manager.cleanup_expired()

    assert removed == 1
    assert share1.share_id not in manager.shares
    assert share2.share_id in manager.shares
