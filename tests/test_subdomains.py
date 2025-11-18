"""Tests for subdomain management."""

import pytest
import time
from pytunnel.common.subdomains import SubdomainManager


def test_valid_subdomain():
    """Test subdomain validation."""
    manager = SubdomainManager()

    # Valid subdomains
    assert manager.is_valid_subdomain("myapp")
    assert manager.is_valid_subdomain("my-app")
    assert manager.is_valid_subdomain("app123")
    assert manager.is_valid_subdomain("abc")

    # Invalid subdomains
    assert not manager.is_valid_subdomain("ab")  # Too short
    assert not manager.is_valid_subdomain("-myapp")  # Starts with hyphen
    assert not manager.is_valid_subdomain("myapp-")  # Ends with hyphen
    assert not manager.is_valid_subdomain("My-App")  # Uppercase
    assert not manager.is_valid_subdomain("my_app")  # Underscore
    assert not manager.is_valid_subdomain("www")  # Reserved


def test_register_subdomain():
    """Test subdomain registration."""
    manager = SubdomainManager()

    # Register subdomain
    assert manager.register_subdomain("myapp", "client123")
    assert manager.get_client_for_subdomain("myapp") == "client123"
    assert manager.get_subdomain_for_client("client123") == "myapp"


def test_duplicate_registration():
    """Test that duplicate subdomain registration fails."""
    manager = SubdomainManager()

    manager.register_subdomain("myapp", "client123")

    # Try to register same subdomain
    assert not manager.register_subdomain("myapp", "client456")


def test_unregister_subdomain():
    """Test subdomain unregistration."""
    manager = SubdomainManager()

    manager.register_subdomain("myapp", "client123")
    assert manager.get_client_for_subdomain("myapp") == "client123"

    # Unregister
    assert manager.unregister_subdomain("myapp", "client123")
    assert manager.get_client_for_subdomain("myapp") is None


def test_unregister_wrong_client():
    """Test that unregistering with wrong client ID fails."""
    manager = SubdomainManager()

    manager.register_subdomain("myapp", "client123")

    # Try to unregister with wrong client ID
    assert not manager.unregister_subdomain("myapp", "wrongclient")
    assert manager.get_client_for_subdomain("myapp") == "client123"


def test_unregister_client():
    """Test unregistering all subdomains for a client."""
    manager = SubdomainManager()

    manager.register_subdomain("myapp", "client123")
    manager.unregister_client("client123")

    assert manager.get_subdomain_for_client("client123") is None
    assert manager.get_client_for_subdomain("myapp") is None


def test_subdomain_expiration():
    """Test subdomain expiration."""
    manager = SubdomainManager()

    # Register with 1 second TTL
    manager.register_subdomain("myapp", "client123", ttl=1)
    assert manager.get_client_for_subdomain("myapp") == "client123"

    # Wait for expiration
    time.sleep(1.1)

    # Should return None after expiration
    assert manager.get_client_for_subdomain("myapp") is None


def test_cleanup_expired():
    """Test cleaning up expired subdomains."""
    manager = SubdomainManager()

    # Register some subdomains
    manager.register_subdomain("app1", "client1", ttl=1)
    manager.register_subdomain("app2", "client2")  # No expiration
    manager.register_subdomain("app3", "client3", ttl=1)

    # Wait for expiration
    time.sleep(1.1)

    # Cleanup
    removed = manager.cleanup_expired()
    assert removed == 2

    # Only app2 should remain
    assert manager.get_client_for_subdomain("app1") is None
    assert manager.get_client_for_subdomain("app2") == "client2"
    assert manager.get_client_for_subdomain("app3") is None


def test_full_domain():
    """Test getting full domain name."""
    manager = SubdomainManager(base_domain="tunnel.example.com")

    assert manager.get_full_domain("myapp") == "myapp.tunnel.example.com"


def test_reserved_subdomains():
    """Test reserved subdomain handling."""
    manager = SubdomainManager()

    # Try to register reserved subdomain
    assert not manager.is_valid_subdomain("www")
    assert not manager.is_valid_subdomain("api")
    assert not manager.is_valid_subdomain("admin")

    # Add custom reservation
    manager.reserve_subdomain("custom")
    assert not manager.is_valid_subdomain("custom")

    # Remove reservation
    manager.unreserve_subdomain("custom")
    assert manager.is_valid_subdomain("custom")


def test_stats():
    """Test subdomain statistics."""
    manager = SubdomainManager()

    manager.register_subdomain("app1", "client1")
    manager.register_subdomain("app2", "client2", ttl=1)

    stats = manager.get_stats()
    assert stats['total'] == 2
    assert stats['active'] == 2

    # Wait for one to expire
    time.sleep(1.1)

    stats = manager.get_stats()
    assert stats['expired'] == 1
    assert stats['active'] == 1
