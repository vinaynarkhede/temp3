"""Tests for compliance features."""

import pytest
import time
import tempfile
from pathlib import Path

from pytunnel.common.compliance import (
    AuditLogger, AuditEventType, GDPRManager,
    DataRetentionManager, RetentionPolicy, ComplianceManager
)


def test_audit_logging_basic():
    """Test basic audit logging."""
    logger = AuditLogger()

    # Log an event
    entry = logger.log_event(
        AuditEventType.USER_LOGIN,
        user_id="user123",
        ip_address="192.168.1.1",
        details={"method": "password"}
    )

    assert entry.event_type == AuditEventType.USER_LOGIN.value
    assert entry.user_id == "user123"
    assert entry.ip_address == "192.168.1.1"
    assert entry.details["method"] == "password"
    assert entry.previous_hash is None  # First entry
    assert entry.entry_hash is not None


def test_audit_log_hash_chain():
    """Test cryptographic hash chain in audit log."""
    logger = AuditLogger()

    # Log multiple events
    entry1 = logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
    entry2 = logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")
    entry3 = logger.log_event(AuditEventType.SHARE_CREATED, user_id="user1")

    # Check hash chain
    assert entry1.previous_hash is None
    assert entry2.previous_hash == entry1.entry_hash
    assert entry3.previous_hash == entry2.entry_hash

    # Verify integrity
    is_valid, errors = logger.verify_integrity()
    assert is_valid
    assert len(errors) == 0


def test_audit_log_tampering_detection():
    """Test detection of tampered audit log."""
    logger = AuditLogger()

    # Log events
    entry1 = logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
    entry2 = logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")

    # Tamper with entry
    logger.entries[0].details["tampered"] = True

    # Verify should fail
    is_valid, errors = logger.verify_integrity()
    assert not is_valid
    assert len(errors) > 0


def test_audit_log_filtering():
    """Test audit log filtering."""
    logger = AuditLogger()

    # Log various events
    logger.log_event(AuditEventType.USER_LOGIN, user_id="user1")
    logger.log_event(AuditEventType.USER_LOGIN, user_id="user2")
    logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")
    time.sleep(0.01)
    logger.log_event(AuditEventType.TUNNEL_DELETED, user_id="user1")

    # Filter by user
    user1_entries = logger.get_entries(user_id="user1")
    assert len(user1_entries) == 3

    # Filter by event type
    login_entries = logger.get_entries(event_type=AuditEventType.USER_LOGIN.value)
    assert len(login_entries) == 2

    # Filter by time
    now = time.time()
    old_entries = logger.get_entries(end_time=now - 1)
    assert len(old_entries) == 3


def test_audit_log_persistence():
    """Test audit log file persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(storage_path)

        # Log events
        logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
        logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")

        # Check file exists
        assert storage_path.exists()

        # Check file contains entries
        with open(storage_path) as f:
            lines = f.readlines()
            assert len(lines) == 2


def test_audit_log_export():
    """Test audit log export to JSON."""
    logger = AuditLogger()

    logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
    logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")

    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "export.json"
        logger.export_to_json(export_path)

        assert export_path.exists()

        import json
        with open(export_path) as f:
            data = json.load(f)

        assert "entries" in data
        assert len(data["entries"]) == 2
        assert "integrity_check" in data
        assert data["integrity_check"] is True


def test_retention_policy_defaults():
    """Test retention policy defaults."""
    policy = RetentionPolicy()

    assert policy.log_retention_days == 90
    assert policy.share_retention_days == 30
    assert policy.traffic_retention_days == 7
    assert policy.auto_cleanup_enabled is True


def test_retention_manager_cleanup_timing():
    """Test retention manager cleanup timing."""
    policy = RetentionPolicy(auto_cleanup_enabled=True)
    manager = DataRetentionManager(policy)

    # Should cleanup on first run
    assert manager.should_cleanup()

    # Mark cleanup as done
    manager.last_cleanup = time.time()

    # Should not cleanup immediately
    assert not manager.should_cleanup()


def test_retention_manager_audit_cleanup():
    """Test audit log cleanup based on retention."""
    policy = RetentionPolicy(log_retention_days=1)
    manager = DataRetentionManager(policy)
    logger = AuditLogger()

    # Create old and new entries
    old_timestamp = time.time() - (2 * 86400)  # 2 days ago
    new_timestamp = time.time()

    entry1 = logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
    entry1.timestamp = old_timestamp

    entry2 = logger.log_event(AuditEventType.USER_CREATED, user_id="user2")
    entry2.timestamp = new_timestamp

    # Run cleanup
    stats = manager.cleanup_old_data(audit_logger=logger)

    # Should have removed 1 old entry
    assert stats["audit_logs_removed"] == 1
    assert len(logger.entries) == 1
    assert logger.entries[0].user_id == "user2"


def test_gdpr_export_user_data():
    """Test GDPR user data export."""
    logger = AuditLogger()
    gdpr = GDPRManager(logger)

    # Create some user data
    logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
    logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")
    logger.log_event(AuditEventType.USER_CREATED, user_id="user2")

    # Export user1 data
    data = gdpr.export_user_data("user1")

    assert data["user_id"] == "user1"
    assert "export_timestamp" in data
    assert "data" in data
    assert "audit_logs" in data["data"]
    assert len(data["data"]["audit_logs"]) == 2

    # Should log the export event
    assert len(logger.entries) == 4  # 3 original + 1 export event


def test_gdpr_delete_user_data():
    """Test GDPR user data deletion."""
    logger = AuditLogger()
    gdpr = GDPRManager(logger)

    # Create user data
    logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
    logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")
    logger.log_event(AuditEventType.USER_CREATED, user_id="user2")

    assert len(logger.entries) == 3

    # Delete user1 data (including logs)
    stats = gdpr.delete_user_data("user1", delete_logs=True)

    # Should have deleted 2 entries
    assert stats["audit_logs_deleted"] == 2

    # Should still have user2's entry + deletion event
    assert len(logger.entries) == 2

    # Verify user1 data is gone
    user1_entries = logger.get_entries(user_id="user1")
    # Should only have the deletion event
    assert len(user1_entries) == 1
    assert user1_entries[0].event_type == AuditEventType.DATA_DELETED.value


def test_gdpr_delete_preserves_audit():
    """Test that deletion preserves audit trail by default."""
    logger = AuditLogger()
    gdpr = GDPRManager(logger)

    # Create user data
    logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
    logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")

    # Delete without deleting logs (default)
    stats = gdpr.delete_user_data("user1", delete_logs=False)

    # Audit logs should be preserved
    assert "audit_logs_deleted" not in stats

    # Should have deletion event
    last_entry = logger.entries[-1]
    assert last_entry.event_type == AuditEventType.DATA_DELETED.value


def test_compliance_manager_integration():
    """Test integrated compliance manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir)
        manager = ComplianceManager(storage_path)

        # Log some events
        manager.audit_logger.log_event(
            AuditEventType.USER_CREATED,
            user_id="user1"
        )
        manager.audit_logger.log_event(
            AuditEventType.TUNNEL_CREATED,
            user_id="user1"
        )

        # Get compliance status
        status = manager.get_compliance_status()

        assert status["audit_log_integrity"] is True
        assert status["total_audit_entries"] == 2
        assert status["gdpr_ready"] is True
        assert "retention_policy" in status


def test_compliance_status_with_errors():
    """Test compliance status reports errors."""
    manager = ComplianceManager()

    # Create valid entries
    manager.audit_logger.log_event(AuditEventType.USER_CREATED, user_id="user1")
    manager.audit_logger.log_event(AuditEventType.TUNNEL_CREATED, user_id="user1")

    # Tamper with entry
    manager.audit_logger.entries[0].details["tampered"] = True

    # Get status
    status = manager.get_compliance_status()

    assert status["audit_log_integrity"] is False
    assert len(status["audit_log_errors"]) > 0


def test_retention_policy_custom():
    """Test custom retention policy."""
    policy = RetentionPolicy(
        log_retention_days=30,
        share_retention_days=7,
        traffic_retention_days=1,
        auto_cleanup_enabled=False
    )

    manager = DataRetentionManager(policy)

    assert manager.policy.log_retention_days == 30
    assert manager.policy.auto_cleanup_enabled is False

    # Should not cleanup when disabled
    assert not manager.should_cleanup()


def test_audit_entry_limit():
    """Test audit entry retrieval limit."""
    logger = AuditLogger()

    # Create many entries
    for i in range(150):
        logger.log_event(AuditEventType.USER_LOGIN, user_id=f"user{i}")

    # Get with default limit
    entries = logger.get_entries()
    assert len(entries) == 100  # Default limit

    # Get with custom limit
    entries = logger.get_entries(limit=50)
    assert len(entries) == 50

    # Should get most recent entries
    assert entries[-1].user_id == "user149"
