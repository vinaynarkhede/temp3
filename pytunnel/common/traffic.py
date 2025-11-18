"""Traffic inspection and logging."""

import time
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from collections import deque
import threading


@dataclass
class TrafficLog:
    """Represents a single traffic log entry."""
    timestamp: float
    client_id: str
    request_id: str
    method: str
    path: str
    status: Optional[int]
    request_size: int
    response_size: int
    duration_ms: float
    remote_addr: Optional[str] = None
    user_agent: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class TrafficInspector:
    """Inspects and logs traffic through tunnels."""

    def __init__(self, max_logs: int = 1000):
        self.max_logs = max_logs
        self.logs: deque = deque(maxlen=max_logs)
        self.lock = threading.Lock()
        self.stats: Dict[str, Dict[str, Any]] = {}

    def log_request(
        self,
        client_id: str,
        request_id: str,
        method: str,
        path: str,
        status: Optional[int],
        request_size: int,
        response_size: int,
        duration_ms: float,
        remote_addr: Optional[str] = None,
        user_agent: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log a traffic entry."""
        log_entry = TrafficLog(
            timestamp=time.time(),
            client_id=client_id,
            request_id=request_id,
            method=method,
            path=path,
            status=status,
            request_size=request_size,
            response_size=response_size,
            duration_ms=duration_ms,
            remote_addr=remote_addr,
            user_agent=user_agent,
            error=error
        )

        with self.lock:
            self.logs.append(log_entry)
            self._update_stats(log_entry)

    def _update_stats(self, log: TrafficLog):
        """Update statistics for a client."""
        client_id = log.client_id

        if client_id not in self.stats:
            self.stats[client_id] = {
                'total_requests': 0,
                'total_bytes_in': 0,
                'total_bytes_out': 0,
                'avg_response_time': 0.0,
                'status_codes': {},
                'methods': {},
                'errors': 0,
                'first_seen': log.timestamp,
                'last_seen': log.timestamp
            }

        stats = self.stats[client_id]
        stats['total_requests'] += 1
        stats['total_bytes_in'] += log.request_size
        stats['total_bytes_out'] += log.response_size
        stats['last_seen'] = log.timestamp

        # Update average response time
        n = stats['total_requests']
        stats['avg_response_time'] = (
            (stats['avg_response_time'] * (n - 1) + log.duration_ms) / n
        )

        # Count status codes
        if log.status:
            status_str = str(log.status)
            stats['status_codes'][status_str] = stats['status_codes'].get(status_str, 0) + 1

        # Count methods
        stats['methods'][log.method] = stats['methods'].get(log.method, 0) + 1

        # Count errors
        if log.error:
            stats['errors'] += 1

    def get_logs(
        self,
        client_id: Optional[str] = None,
        limit: int = 100
    ) -> List[TrafficLog]:
        """Get recent logs, optionally filtered by client."""
        with self.lock:
            logs = list(self.logs)

        if client_id:
            logs = [log for log in logs if log.client_id == client_id]

        return logs[-limit:]

    def get_stats(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics, optionally for a specific client."""
        with self.lock:
            if client_id:
                return self.stats.get(client_id, {})
            return dict(self.stats)

    def clear_logs(self, client_id: Optional[str] = None):
        """Clear logs, optionally for a specific client."""
        with self.lock:
            if client_id:
                self.logs = deque(
                    (log for log in self.logs if log.client_id != client_id),
                    maxlen=self.max_logs
                )
                if client_id in self.stats:
                    del self.stats[client_id]
            else:
                self.logs.clear()
                self.stats.clear()

    def export_logs(self, filename: str, client_id: Optional[str] = None):
        """Export logs to a JSON file."""
        logs = self.get_logs(client_id=client_id, limit=self.max_logs)
        log_dicts = [log.to_dict() for log in logs]

        with open(filename, 'w') as f:
            json.dump(log_dicts, f, indent=2)

    def get_bandwidth_usage(self, client_id: str) -> Dict[str, int]:
        """Get bandwidth usage for a client."""
        stats = self.stats.get(client_id, {})
        return {
            'bytes_in': stats.get('total_bytes_in', 0),
            'bytes_out': stats.get('total_bytes_out', 0),
            'total': stats.get('total_bytes_in', 0) + stats.get('total_bytes_out', 0)
        }


# Global instance
_traffic_inspector = None


def get_traffic_inspector() -> TrafficInspector:
    """Get the global traffic inspector instance."""
    global _traffic_inspector
    if _traffic_inspector is None:
        _traffic_inspector = TrafficInspector()
    return _traffic_inspector
