"""Multi-protocol support for tunneling."""

from enum import Enum
from typing import Dict, Any, Optional
import json


class TunnelProtocol(Enum):
    """Supported tunnel protocols."""
    HTTP = "http"
    HTTPS = "https"
    WEBSOCKET = "websocket"
    TCP = "tcp"
    GRPC = "grpc"


class ProtocolDetector:
    """Detects the protocol of incoming connections."""

    @staticmethod
    def detect_from_request(headers: Dict[str, str], path: str) -> TunnelProtocol:
        """Detect protocol from HTTP request headers."""
        # Check for WebSocket upgrade
        if headers.get('Upgrade', '').lower() == 'websocket':
            return TunnelProtocol.WEBSOCKET

        # Check for gRPC
        content_type = headers.get('Content-Type', '')
        if 'application/grpc' in content_type:
            return TunnelProtocol.GRPC

        # Check for HTTPS (from X-Forwarded-Proto or similar)
        proto = headers.get('X-Forwarded-Proto', '').lower()
        if proto == 'https':
            return TunnelProtocol.HTTPS

        # Default to HTTP
        return TunnelProtocol.HTTP

    @staticmethod
    def is_websocket_upgrade(headers: Dict[str, str]) -> bool:
        """Check if request is a WebSocket upgrade."""
        upgrade = headers.get('Upgrade', '').lower()
        connection = headers.get('Connection', '').lower()
        return upgrade == 'websocket' and 'upgrade' in connection


class WebSocketTunnelHandler:
    """Handler for WebSocket protocol tunneling."""

    @staticmethod
    def create_upgrade_request(path: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Create WebSocket upgrade request."""
        return {
            'type': 'websocket_upgrade',
            'path': path,
            'headers': headers
        }

    @staticmethod
    def create_frame_message(data: bytes, opcode: int = 1) -> Dict[str, Any]:
        """Create WebSocket frame message."""
        import base64
        return {
            'type': 'websocket_frame',
            'data': base64.b64encode(data).decode('utf-8'),
            'opcode': opcode
        }

    @staticmethod
    def create_close_message(code: int = 1000, reason: str = '') -> Dict[str, Any]:
        """Create WebSocket close message."""
        return {
            'type': 'websocket_close',
            'code': code,
            'reason': reason
        }


class GRPCTunnelHandler:
    """Handler for gRPC protocol tunneling."""

    @staticmethod
    def create_grpc_request(
        method: str,
        headers: Dict[str, str],
        data: bytes
    ) -> Dict[str, Any]:
        """Create gRPC request message."""
        import base64
        return {
            'type': 'grpc_request',
            'method': method,
            'headers': headers,
            'data': base64.b64encode(data).decode('utf-8')
        }

    @staticmethod
    def create_grpc_response(
        status: int,
        headers: Dict[str, str],
        data: bytes,
        trailers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create gRPC response message."""
        import base64
        return {
            'type': 'grpc_response',
            'status': status,
            'headers': headers,
            'data': base64.b64encode(data).decode('utf-8'),
            'trailers': trailers or {}
        }

    @staticmethod
    def parse_grpc_status(headers: Dict[str, str]) -> Optional[int]:
        """Parse gRPC status from headers."""
        grpc_status = headers.get('grpc-status')
        if grpc_status:
            try:
                return int(grpc_status)
            except ValueError:
                pass
        return None


class ProtocolConfig:
    """Configuration for protocol support."""

    def __init__(self):
        self.enabled_protocols = {
            TunnelProtocol.HTTP,
            TunnelProtocol.HTTPS,
        }
        self.websocket_enabled = False
        self.tcp_enabled = False
        self.grpc_enabled = False

    def enable_protocol(self, protocol: TunnelProtocol):
        """Enable a protocol."""
        self.enabled_protocols.add(protocol)

        if protocol == TunnelProtocol.WEBSOCKET:
            self.websocket_enabled = True
        elif protocol == TunnelProtocol.TCP:
            self.tcp_enabled = True
        elif protocol == TunnelProtocol.GRPC:
            self.grpc_enabled = True

    def disable_protocol(self, protocol: TunnelProtocol):
        """Disable a protocol."""
        self.enabled_protocols.discard(protocol)

        if protocol == TunnelProtocol.WEBSOCKET:
            self.websocket_enabled = False
        elif protocol == TunnelProtocol.TCP:
            self.tcp_enabled = False
        elif protocol == TunnelProtocol.GRPC:
            self.grpc_enabled = False

    def is_enabled(self, protocol: TunnelProtocol) -> bool:
        """Check if protocol is enabled."""
        return protocol in self.enabled_protocols

    def get_enabled_protocols(self) -> set:
        """Get set of enabled protocols."""
        return self.enabled_protocols.copy()


# Global instance
_protocol_config = None


def get_protocol_config() -> ProtocolConfig:
    """Get the global protocol config instance."""
    global _protocol_config
    if _protocol_config is None:
        _protocol_config = ProtocolConfig()
    return _protocol_config
