"""TCP tunnel protocol definitions."""

import json
from enum import Enum
from typing import Optional, Dict, Any


class TCPMessageType(Enum):
    """Message types for TCP tunnel protocol."""

    # Connection messages
    TCP_CONNECT = "tcp_connect"
    TCP_CONNECT_ACK = "tcp_connect_ack"
    TCP_DISCONNECT = "tcp_disconnect"

    # Data messages
    TCP_DATA = "tcp_data"
    TCP_ERROR = "tcp_error"


class TCPTunnelMessage:
    """Represents a message in the TCP tunnel protocol."""

    def __init__(
        self,
        msg_type: TCPMessageType,
        connection_id: str,
        data: Optional[Dict[str, Any]] = None
    ):
        self.msg_type = msg_type
        self.connection_id = connection_id
        self.data = data or {}

    def to_json(self) -> str:
        """Serialize message to JSON."""
        return json.dumps({
            "type": self.msg_type.value,
            "connection_id": self.connection_id,
            "data": self.data
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'TCPTunnelMessage':
        """Deserialize message from JSON."""
        obj = json.loads(json_str)
        return cls(
            msg_type=TCPMessageType(obj["type"]),
            connection_id=obj["connection_id"],
            data=obj.get("data", {})
        )

    def __repr__(self) -> str:
        return f"TCPTunnelMessage(type={self.msg_type.value}, conn={self.connection_id})"


def create_tcp_connect(connection_id: str, host: str, port: int) -> TCPTunnelMessage:
    """Create a TCP connect message."""
    return TCPTunnelMessage(
        msg_type=TCPMessageType.TCP_CONNECT,
        connection_id=connection_id,
        data={"host": host, "port": port}
    )


def create_tcp_connect_ack(connection_id: str, success: bool, error: Optional[str] = None) -> TCPTunnelMessage:
    """Create a TCP connect acknowledgment."""
    return TCPTunnelMessage(
        msg_type=TCPMessageType.TCP_CONNECT_ACK,
        connection_id=connection_id,
        data={"success": success, "error": error}
    )


def create_tcp_data(connection_id: str, data: bytes) -> TCPTunnelMessage:
    """Create a TCP data message."""
    import base64
    return TCPTunnelMessage(
        msg_type=TCPMessageType.TCP_DATA,
        connection_id=connection_id,
        data={"data": base64.b64encode(data).decode('utf-8')}
    )


def create_tcp_disconnect(connection_id: str, reason: Optional[str] = None) -> TCPTunnelMessage:
    """Create a TCP disconnect message."""
    return TCPTunnelMessage(
        msg_type=TCPMessageType.TCP_DISCONNECT,
        connection_id=connection_id,
        data={"reason": reason}
    )


def create_tcp_error(connection_id: str, error: str) -> TCPTunnelMessage:
    """Create a TCP error message."""
    return TCPTunnelMessage(
        msg_type=TCPMessageType.TCP_ERROR,
        connection_id=connection_id,
        data={"error": error}
    )
