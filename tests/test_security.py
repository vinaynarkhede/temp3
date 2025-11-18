"""Tests for advanced security features."""

import pytest
import time
from pytunnel.common.security import (
    SecurityManager, SecurityConfig, SecurityPreset,
    IPFilter, ConnectionTracker, DDoSProtection
)


def test_security_presets():
    """Test security configuration presets."""
    basic = SecurityConfig.from_preset(SecurityPreset.BASIC)
    standard = SecurityConfig.from_preset(SecurityPreset.STANDARD)
    paranoid = SecurityConfig.from_preset(SecurityPreset.PARANOID)

    # Basic should be most permissive
    assert basic.max_connections_per_ip > standard.max_connections_per_ip
    assert standard.max_connections_per_ip > paranoid.max_connections_per_ip

    # Paranoid should require signatures
    assert paranoid.require_signature
    assert not basic.require_signature


def test_ip_filter_whitelist():
    """Test IP whitelist filtering."""
    config = SecurityConfig(
        ip_whitelist={"192.168.1.1", "10.0.0.0/24"}
    )

    ip_filter = IPFilter(config)

    # Allowed individual IP
    allowed, reason = ip_filter.is_allowed("192.168.1.1")
    assert allowed

    # Allowed network range
    allowed, reason = ip_filter.is_allowed("10.0.0.50")
    assert allowed

    # Not allowed
    allowed, reason = ip_filter.is_allowed("192.168.1.2")
    assert not allowed


def test_ip_filter_blacklist():
    """Test IP blacklist filtering."""
    config = SecurityConfig(
        ip_blacklist={"1.2.3.4", "5.6.7.0/24"}
    )

    ip_filter = IPFilter(config)

    # Blocked individual IP
    allowed, reason = ip_filter.is_allowed("1.2.3.4")
    assert not allowed

    # Blocked network range
    allowed, reason = ip_filter.is_allowed("5.6.7.100")
    assert not allowed

    # Allowed
    allowed, reason = ip_filter.is_allowed("8.8.8.8")
    assert allowed


def test_connection_limits():
    """Test connection limiting."""
    config = SecurityConfig(
        max_connections_per_ip=2,
        max_connections_total=10
    )

    tracker = ConnectionTracker(config)

    # First connection should succeed
    allowed, reason = tracker.can_connect("192.168.1.1")
    assert allowed

    tracker.register_connection("192.168.1.1")

    # Second connection should succeed
    allowed, reason = tracker.can_connect("192.168.1.1")
    assert allowed

    tracker.register_connection("192.168.1.1")

    # Third connection should fail (max 2 per IP)
    allowed, reason = tracker.can_connect("192.168.1.1")
    assert not allowed


def test_connection_rate_limiting():
    """Test connection rate limiting."""
    config = SecurityConfig(
        connection_rate_limit=5  # 5 per minute
    )

    tracker = ConnectionTracker(config)

    # First 5 connections should succeed
    for i in range(5):
        allowed, _ = tracker.can_connect("192.168.1.1")
        assert allowed
        tracker.register_connection("192.168.1.1")

    # 6th should be blocked
    allowed, reason = tracker.can_connect("192.168.1.1")
    assert not allowed
    assert "blocked" in reason.lower()


def test_ddos_request_rate_limiting():
    """Test request rate limiting for DDoS protection."""
    config = SecurityConfig(
        request_rate_limit=10  # 10 per minute
    )

    ddos = DDoSProtection(config)

    # First 10 requests should succeed
    for _ in range(10):
        allowed, _ = ddos.check_request_rate("192.168.1.1")
        assert allowed

    # 11th should fail
    allowed, reason = ddos.check_request_rate("192.168.1.1")
    assert not allowed


def test_ddos_auto_blocking():
    """Test automatic IP blocking after violations."""
    config = SecurityConfig(
        request_rate_limit=5
    )

    ddos = DDoSProtection(config)

    # Violate rate limit 3 times
    for _ in range(3):
        # Max out rate limit
        for _ in range(6):
            ddos.check_request_rate("192.168.1.1")

    # Should be auto-blocked now
    blocked_ips = ddos.get_blocked_ips()
    assert len(blocked_ips) > 0
    assert any(ip['ip'] == "192.168.1.1" for ip in blocked_ips)


def test_security_score_calculation():
    """Test security score calculation."""
    # Basic config (low score)
    basic_config = SecurityConfig.from_preset(SecurityPreset.BASIC)
    basic_manager = SecurityManager(basic_config)
    basic_score = basic_manager.get_security_score()

    # Paranoid config (high score)
    paranoid_config = SecurityConfig.from_preset(SecurityPreset.PARANOID)
    paranoid_manager = SecurityManager(paranoid_config)
    paranoid_score = paranoid_manager.get_security_score()

    # Paranoid should have higher score
    assert paranoid_score > basic_score
    assert paranoid_score >= 80  # Should be at least 80


def test_security_manager_integration():
    """Test integrated security manager."""
    config = SecurityConfig(
        ip_whitelist={"192.168.1.0/24"},
        max_connections_per_ip=5
    )

    manager = SecurityManager(config)

    # Allowed IP
    allowed, _ = manager.check_connection("192.168.1.100")
    assert allowed

    # Not whitelisted IP
    allowed, reason = manager.check_connection("10.0.0.1")
    assert not allowed

    # Register connections
    manager.register_connection("192.168.1.100")
    manager.register_connection("192.168.1.100")

    # Unregister
    manager.unregister_connection("192.168.1.100")

    # Check request rate
    allowed, _ = manager.check_request("192.168.1.100")
    assert allowed


def test_get_security_stats():
    """Test getting security statistics."""
    config = SecurityConfig.from_preset(SecurityPreset.STANDARD)
    manager = SecurityManager(config)

    # Register some connections
    manager.register_connection("192.168.1.1")
    manager.register_connection("192.168.1.2")

    stats = manager.get_stats()

    assert 'security_score' in stats
    assert 'connections' in stats
    assert 'blocked_ips' in stats
    assert 'config' in stats
    assert stats['connections']['total_connections'] == 2


def test_unblock_ip():
    """Test manually unblocking an IP."""
    config = SecurityConfig(request_rate_limit=5)
    ddos = DDoSProtection(config)

    # Violate and get blocked
    for _ in range(3):
        for _ in range(6):
            ddos.check_request_rate("192.168.1.1")

    # Verify blocked
    assert len(ddos.get_blocked_ips()) > 0

    # Unblock
    ddos.unblock_ip("192.168.1.1")

    # Verify unblocked
    blocked = [ip for ip in ddos.get_blocked_ips() if ip['ip'] == "192.168.1.1"]
    assert len(blocked) == 0
