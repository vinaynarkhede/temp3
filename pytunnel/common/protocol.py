"""Protocol definitions for tunnel communication."""

import json
from enum import Enum
from typing import Dict, Any, Optional


class MessageType(Enum):
    """Message types for tunnel protocol."""

    # Control messages
    REGISTER = "register"
    REGISTER_ACK = "register_ack"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"

    # Data messages
    HTTP_REQUEST = "http_request"
    HTTP_RESPONSE = "http_response"
    ERROR = "error"


class TunnelMessage:
    """Represents a message in the tunnel protocol."""

    def __init__(
        self,
        msg_type: MessageType,
        request_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        self.msg_type = msg_type
        self.request_id = request_id
        self.data = data or {}

    def to_json(self) -> str:
        """Serialize message to JSON."""
        return json.dumps({
            "type": self.msg_type.value,
            "request_id": self.request_id,
            "data": self.data
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'TunnelMessage':
        """Deserialize message from JSON."""
        obj = json.loads(json_str)
        return cls(
            msg_type=MessageType(obj["type"]),
            request_id=obj.get("request_id"),
            data=obj.get("data", {})
        )

    def __repr__(self) -> str:
        return f"TunnelMessage(type={self.msg_type.value}, request_id={self.request_id})"


def create_register_message(client_id: str) -> TunnelMessage:
    """Create a registration message."""
    return TunnelMessage(
        msg_type=MessageType.REGISTER,
        data={"client_id": client_id}
    )


def create_register_ack(client_id: str, tunnel_url: str) -> TunnelMessage:
    """Create a registration acknowledgment."""
    return TunnelMessage(
        msg_type=MessageType.REGISTER_ACK,
        data={"client_id": client_id, "tunnel_url": tunnel_url}
    )


def create_http_request(request_id: str, method: str, path: str,
                       headers: Dict[str, str], body: bytes) -> TunnelMessage:
    """Create an HTTP request message."""
    return TunnelMessage(
        msg_type=MessageType.HTTP_REQUEST,
        request_id=request_id,
        data={
            "method": method,
            "path": path,
            "headers": headers,
            "body": body.decode('utf-8', errors='replace') if body else ""
        }
    )


def create_http_response(request_id: str, status: int,
                        headers: Dict[str, str], body: bytes) -> TunnelMessage:
    """Create an HTTP response message."""
    return TunnelMessage(
        msg_type=MessageType.HTTP_RESPONSE,
        request_id=request_id,
        data={
            "status": status,
            "headers": headers,
            "body": body.decode('utf-8', errors='replace') if body else ""
        }
    )


def create_error_message(request_id: str, error: str) -> TunnelMessage:
    """Create an error message."""
    return TunnelMessage(
        msg_type=MessageType.ERROR,
        request_id=request_id,
        data={"error": error}
    )
