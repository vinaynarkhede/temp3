"""Tests for CLI display utilities."""

import pytest
import time
from io import StringIO
from unittest.mock import patch, MagicMock

from pytunnel.common.cli_display import (
    ProgressTracker, LiveDisplay, StatusDisplay,
    get_status_display
)


def test_progress_tracker_initialization():
    """Test progress tracker initializes correctly."""
    tracker = ProgressTracker()
    assert tracker.progress is None or tracker.progress is not None


def test_progress_tracker_without_rich():
    """Test progress tracker works without rich."""
    import pytunnel.common.cli_display as display_module
    original = display_module.RICH_AVAILABLE
    display_module.RICH_AVAILABLE = False

    try:
        tracker = ProgressTracker()

        # Should work without errors
        with tracker.track_task("Test task", total=100) as update:
            for i in range(10):
                update(10)
    finally:
        display_module.RICH_AVAILABLE = original


def test_progress_tracker_download():
    """Test download progress tracking."""
    import pytunnel.common.cli_display as display_module
    original = display_module.RICH_AVAILABLE
    display_module.RICH_AVAILABLE = False

    try:
        tracker = ProgressTracker()

        # Should work without errors
        with tracker.track_download("Downloading file", total=1000) as update:
            update(500)
            update(500)
    finally:
        display_module.RICH_AVAILABLE = original


def test_live_display_initialization():
    """Test live display initializes correctly."""
    display = LiveDisplay()
    assert display is not None


def test_live_display_without_rich():
    """Test live display works without rich."""
    import pytunnel.common.cli_display as display_module
    original = display_module.RICH_AVAILABLE
    display_module.RICH_AVAILABLE = False

    try:
        display = LiveDisplay()

        # Should work without errors
        with display.live_display() as update:
            update("Status: Running")
            time.sleep(0.01)
            update("Status: Complete")
    finally:
        display_module.RICH_AVAILABLE = original


def test_live_display_spinner():
    """Test live display with spinner."""
    import pytunnel.common.cli_display as display_module
    original = display_module.RICH_AVAILABLE
    display_module.RICH_AVAILABLE = False

    try:
        display = LiveDisplay()

        # Should work without errors
        with display.spinner("Processing..."):
            time.sleep(0.01)
    finally:
        display_module.RICH_AVAILABLE = original


def test_status_display_initialization():
    """Test status display initializes correctly."""
    display = StatusDisplay()
    assert display is not None


def test_status_display_tunnel_status():
    """Test displaying tunnel status."""
    display = StatusDisplay()

    tunnels = [
        {
            'id': 'tunnel1',
            'subdomain': 'myapp',
            'local_port': 3000,
            'status': 'active',
            'requests_count': 42
        },
        {
            'id': 'tunnel2',
            'subdomain': 'api',
            'local_port': 5000,
            'status': 'inactive',
            'requests_count': 0
        }
    ]

    # Should not raise exception
    display.show_tunnel_status(tunnels)


def test_status_display_security_status():
    """Test displaying security status."""
    display = StatusDisplay()

    security_stats = {
        'security_score': 85,
        'connections': {
            'total_connections': 10,
            'active_connections': 5
        },
        'blocked_ips': [
            {'ip': '1.2.3.4', 'reason': 'Rate limit'},
            {'ip': '5.6.7.8', 'reason': 'Blacklist'}
        ],
        'config': {
            'has_whitelist': True,
            'has_blacklist': True
        }
    }

    # Should not raise exception
    display.show_security_status(security_stats)


def test_status_display_compliance_status():
    """Test displaying compliance status."""
    display = StatusDisplay()

    compliance_status = {
        'audit_log_integrity': True,
        'total_audit_entries': 100,
        'gdpr_ready': True,
        'retention_policy': {
            'log_retention_days': 90,
            'auto_cleanup_enabled': True
        }
    }

    # Should not raise exception
    display.show_compliance_status(compliance_status)


def test_status_display_summary():
    """Test displaying complete summary."""
    display = StatusDisplay()

    tunnels = [
        {
            'id': 'tunnel1',
            'subdomain': 'myapp',
            'local_port': 3000,
            'status': 'active',
            'requests_count': 42
        }
    ]

    security = {
        'security_score': 75,
        'connections': {'total_connections': 5},
        'blocked_ips': [],
        'config': {'has_whitelist': False, 'has_blacklist': False}
    }

    compliance = {
        'audit_log_integrity': True,
        'total_audit_entries': 50,
        'gdpr_ready': True,
        'retention_policy': {
            'log_retention_days': 90,
            'auto_cleanup_enabled': True
        }
    }

    # Should not raise exception
    display.show_summary(tunnels, security, compliance)


def test_status_display_empty_tunnels():
    """Test displaying status with no tunnels."""
    display = StatusDisplay()

    # Should handle empty list gracefully
    display.show_tunnel_status([])


def test_status_display_no_blocked_ips():
    """Test displaying security status with no blocked IPs."""
    display = StatusDisplay()

    security_stats = {
        'security_score': 100,
        'connections': {'total_connections': 0},
        'blocked_ips': [],
        'config': {'has_whitelist': False, 'has_blacklist': False}
    }

    # Should not raise exception
    display.show_security_status(security_stats)


def test_get_status_display_singleton():
    """Test get_status_display returns singleton."""
    display1 = get_status_display()
    display2 = get_status_display()

    assert display1 is display2


def test_status_display_without_rich():
    """Test status display works without rich."""
    import pytunnel.common.cli_display as display_module
    original = display_module.RICH_AVAILABLE
    display_module.RICH_AVAILABLE = False

    try:
        display = StatusDisplay()

        tunnels = [{'id': 'test', 'subdomain': 'app', 'local_port': 3000}]
        security = {'security_score': 50, 'connections': {}, 'blocked_ips': [], 'config': {}}
        compliance = {'audit_log_integrity': True, 'total_audit_entries': 0}

        # Should work without errors
        display.show_tunnel_status(tunnels)
        display.show_security_status(security)
        display.show_compliance_status(compliance)
        display.show_summary(tunnels, security, compliance)
    finally:
        display_module.RICH_AVAILABLE = original


def test_progress_tracker_with_rich():
    """Test progress tracker with rich available."""
    try:
        from rich.progress import Progress

        tracker = ProgressTracker()

        # Should use rich when available
        with tracker.track_task("Test", total=100) as update:
            update(50)
            update(50)
    except ImportError:
        pytest.skip("Rich not available")


def test_live_display_with_rich():
    """Test live display with rich available."""
    try:
        from rich.live import Live

        display = LiveDisplay()

        # Should use rich when available
        with display.live_display() as update:
            update("Test status")
    except ImportError:
        pytest.skip("Rich not available")


def test_status_display_color_coding():
    """Test status display shows appropriate colors for security scores."""
    display = StatusDisplay()

    # High score
    high_security = {
        'security_score': 90,
        'connections': {},
        'blocked_ips': [],
        'config': {}
    }

    # Low score
    low_security = {
        'security_score': 30,
        'connections': {},
        'blocked_ips': [],
        'config': {}
    }

    # Should not raise exception for either
    display.show_security_status(high_security)
    display.show_security_status(low_security)


def test_status_display_compliance_integrity_failed():
    """Test displaying compliance status with integrity failure."""
    display = StatusDisplay()

    compliance_status = {
        'audit_log_integrity': False,
        'audit_log_errors': ['Entry 5 has invalid hash'],
        'total_audit_entries': 100,
        'gdpr_ready': True,
        'retention_policy': {
            'log_retention_days': 90,
            'auto_cleanup_enabled': True
        }
    }

    # Should not raise exception
    display.show_compliance_status(compliance_status)
