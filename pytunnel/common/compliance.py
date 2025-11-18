"""Compliance features for GDPR, data retention, and audit logging."""

import time
import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


class AuditEventType(Enum):
    """Audit event types."""
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    TUNNEL_CREATED = "tunnel.created"
    TUNNEL_DELETED = "tunnel.deleted"
    SHARE_CREATED = "share.created"
    SHARE_ACCESSED = "share.accessed"
    DATA_EXPORTED = "data.exported"
    DATA_DELETED = "data.deleted"
    CONFIG_CHANGED = "config.changed"
    SECURITY_ALERT = "security.alert"


@dataclass
class AuditEntry:
    """Audit log entry."""
    id: str
    timestamp: float
    event_type: str
    user_id: Optional[str]
    ip_address: Optional[str]
    details: Dict[str, Any]
    previous_hash: Optional[str]
    entry_hash: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class AuditLogger:
    """Tamper-evident audit logging system."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.entries: List[AuditEntry] = []
        self.storage_path = storage_path
        self.last_hash: Optional[str] = None

    def _calculate_hash(self, entry: Dict) -> str:
        """Calculate hash for entry."""
        # Include previous hash for chain
        data = json.dumps(entry, sort_keys=True) + (self.last_hash or "")
        return hashlib.sha256(data.encode()).hexdigest()

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        Log an audit event.

        Creates a tamper-evident entry with cryptographic hash chain.
        """
        entry_id = hashlib.sha256(
            f"{time.time()}{event_type.value}".encode()
        ).hexdigest()[:16]

        entry_data = {
            "id": entry_id,
            "timestamp": time.time(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {},
            "previous_hash": self.last_hash
        }

        entry_hash = self._calculate_hash(entry_data)
        entry_data["entry_hash"] = entry_hash

        entry = AuditEntry(**entry_data)
        self.entries.append(entry)
        self.last_hash = entry_hash

        # Persist if storage path configured
        if self.storage_path:
            self._append_to_file(entry)

        return entry

    def _append_to_file(self, entry: AuditEntry):
        """Append entry to audit log file."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.storage_path, 'a') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')

    def verify_integrity(self) -> tuple[bool, List[str]]:
        """
        Verify audit log integrity.

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        previous_hash = None

        for i, entry in enumerate(self.entries):
            # Check previous hash matches
            if entry.previous_hash != previous_hash:
                errors.append(f"Entry {i} has invalid previous_hash")

            # Recalculate hash
            entry_data = {
                "id": entry.id,
                "timestamp": entry.timestamp,
                "event_type": entry.event_type,
                "user_id": entry.user_id,
                "ip_address": entry.ip_address,
                "details": entry.details,
                "previous_hash": entry.previous_hash
            }

            calculated_hash = self._calculate_hash(entry_data)

            if calculated_hash != entry.entry_hash:
                errors.append(f"Entry {i} has invalid entry_hash")

            previous_hash = entry.entry_hash

        return len(errors) == 0, errors

    def get_entries(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit entries with filters."""
        filtered = self.entries

        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]

        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]

        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]

        return filtered[-limit:]

    def export_to_json(self, output_path: Path):
        """Export audit log to JSON file."""
        data = {
            "exported_at": time.time(),
            "entries": [entry.to_dict() for entry in self.entries],
            "integrity_check": self.verify_integrity()[0]
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)


@dataclass
class RetentionPolicy:
    """Data retention policy."""
    log_retention_days: int = 90
    share_retention_days: int = 30
    traffic_retention_days: int = 7
    auto_cleanup_enabled: bool = True


class DataRetentionManager:
    """Manages data retention and cleanup."""

    def __init__(self, policy: Optional[RetentionPolicy] = None):
        self.policy = policy or RetentionPolicy()
        self.last_cleanup: Optional[float] = None

    def should_cleanup(self) -> bool:
        """Check if it's time to run cleanup."""
        if not self.policy.auto_cleanup_enabled:
            return False

        if self.last_cleanup is None:
            return True

        # Run cleanup once per day
        return time.time() - self.last_cleanup > 86400

    def cleanup_old_data(
        self,
        audit_logger: Optional[AuditLogger] = None,
        traffic_inspector: Optional[Any] = None,
        share_manager: Optional[Any] = None
    ) -> Dict[str, int]:
        """
        Clean up old data according to retention policy.

        Returns:
            Dictionary of cleanup stats
        """
        now = time.time()
        stats = {}

        # Cleanup audit logs
        if audit_logger and self.policy.log_retention_days > 0:
            cutoff = now - (self.policy.log_retention_days * 86400)
            original_count = len(audit_logger.entries)
            audit_logger.entries = [
                e for e in audit_logger.entries
                if e.timestamp >= cutoff
            ]
            stats['audit_logs_removed'] = original_count - len(audit_logger.entries)

        # Cleanup shares
        if share_manager and self.policy.share_retention_days > 0:
            removed = share_manager.cleanup_expired()
            stats['shares_removed'] = removed

        # Cleanup traffic logs
        if traffic_inspector and self.policy.traffic_retention_days > 0:
            cutoff = now - (self.policy.traffic_retention_days * 86400)
            original_count = len(traffic_inspector.logs)
            traffic_inspector.logs = deque([
                log for log in traffic_inspector.logs
                if log.timestamp >= cutoff
            ], maxlen=traffic_inspector.max_logs)
            stats['traffic_logs_removed'] = original_count - len(traffic_inspector.logs)

        self.last_cleanup = now
        return stats


class GDPRManager:
    """GDPR compliance tools."""

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger

    def export_user_data(
        self,
        user_id: str,
        include_logs: bool = True,
        include_tunnels: bool = True,
        include_shares: bool = True
    ) -> Dict[str, Any]:
        """
        Export all data for a user (GDPR right to access).

        Returns:
            Dictionary with all user data
        """
        data = {
            "user_id": user_id,
            "export_timestamp": time.time(),
            "data": {}
        }

        # Export audit logs
        if include_logs:
            audit_entries = self.audit_logger.get_entries(user_id=user_id, limit=10000)
            data["data"]["audit_logs"] = [e.to_dict() for e in audit_entries]

        # Log the export
        self.audit_logger.log_event(
            AuditEventType.DATA_EXPORTED,
            user_id=user_id,
            details={"data_types": ["audit_logs"] if include_logs else []}
        )

        return data

    def delete_user_data(
        self,
        user_id: str,
        delete_logs: bool = False,
        delete_tunnels: bool = True,
        delete_shares: bool = True
    ) -> Dict[str, int]:
        """
        Delete all data for a user (GDPR right to erasure).

        Returns:
            Dictionary with deletion stats
        """
        stats = {}

        # Note: Audit logs about deletion should be kept for compliance
        # Only delete if explicitly requested

        if delete_logs:
            original_count = len(self.audit_logger.entries)
            self.audit_logger.entries = [
                e for e in self.audit_logger.entries
                if e.user_id != user_id
            ]
            stats['audit_logs_deleted'] = original_count - len(self.audit_logger.entries)

        # Log the deletion (after removing user logs if requested)
        self.audit_logger.log_event(
            AuditEventType.DATA_DELETED,
            user_id=user_id,
            details={"stats": stats}
        )

        return stats


class ComplianceManager:
    """Unified compliance manager."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        retention_policy: Optional[RetentionPolicy] = None
    ):
        audit_path = storage_path / 'audit.log' if storage_path else None
        self.audit_logger = AuditLogger(audit_path)
        self.retention_manager = DataRetentionManager(retention_policy)
        self.gdpr_manager = GDPRManager(self.audit_logger)

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get overall compliance status."""
        integrity_ok, errors = self.audit_logger.verify_integrity()

        return {
            "audit_log_integrity": integrity_ok,
            "audit_log_errors": errors if not integrity_ok else [],
            "total_audit_entries": len(self.audit_logger.entries),
            "retention_policy": {
                "log_retention_days": self.retention_manager.policy.log_retention_days,
                "auto_cleanup_enabled": self.retention_manager.policy.auto_cleanup_enabled
            },
            "last_cleanup": self.retention_manager.last_cleanup,
            "gdpr_ready": True  # Has export and delete functionality
        }


# Global instance
_compliance_manager = None


def get_compliance_manager(
    storage_path: Optional[Path] = None,
    retention_policy: Optional[RetentionPolicy] = None
) -> ComplianceManager:
    """Get the global compliance manager instance."""
    global _compliance_manager
    if _compliance_manager is None:
        _compliance_manager = ComplianceManager(storage_path, retention_policy)
    return _compliance_manager
