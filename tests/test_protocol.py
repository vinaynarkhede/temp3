"""Tests for the tunnel protocol."""

import pytest
from pytunnel.common.protocol import (
    TunnelMessage, MessageType, create_register_message,
    create_register_ack, create_http_request, create_http_response
)


def test_tunnel_message_serialization():
    """Test message serialization and deserialization."""
    msg = TunnelMessage(
        msg_type=MessageType.REGISTER,
        request_id="test123",
        data={"client_id": "abc"}
    )

    # Serialize
    json_str = msg.to_json()
    assert isinstance(json_str, str)

    # Deserialize
    restored = TunnelMessage.from_json(json_str)
    assert restored.msg_type == MessageType.REGISTER
    assert restored.request_id == "test123"
    assert restored.data["client_id"] == "abc"


def test_create_register_message():
    """Test registration message creation."""
    msg = create_register_message("client123")

    assert msg.msg_type == MessageType.REGISTER
    assert msg.data["client_id"] == "client123"


def test_create_register_ack():
    """Test registration acknowledgment creation."""
    msg = create_register_ack("client123", "http://example.com/tunnel")

    assert msg.msg_type == MessageType.REGISTER_ACK
    assert msg.data["client_id"] == "client123"
    assert msg.data["tunnel_url"] == "http://example.com/tunnel"


def test_create_http_request():
    """Test HTTP request message creation."""
    msg = create_http_request(
        request_id="req123",
        method="GET",
        path="/api/test",
        headers={"User-Agent": "Test"},
        body=b"test body"
    )

    assert msg.msg_type == MessageType.HTTP_REQUEST
    assert msg.request_id == "req123"
    assert msg.data["method"] == "GET"
    assert msg.data["path"] == "/api/test"
    assert msg.data["headers"]["User-Agent"] == "Test"
    assert "test body" in msg.data["body"]


def test_create_http_response():
    """Test HTTP response message creation."""
    msg = create_http_response(
        request_id="req123",
        status=200,
        headers={"Content-Type": "text/html"},
        body=b"<html>test</html>"
    )

    assert msg.msg_type == MessageType.HTTP_RESPONSE
    assert msg.request_id == "req123"
    assert msg.data["status"] == 200
    assert msg.data["headers"]["Content-Type"] == "text/html"
    assert "html" in msg.data["body"]


def test_message_roundtrip():
    """Test full message roundtrip."""
    original = create_http_request(
        request_id="test",
        method="POST",
        path="/test",
        headers={"X-Test": "value"},
        body=b"data"
    )

    json_str = original.to_json()
    restored = TunnelMessage.from_json(json_str)

    assert restored.msg_type == original.msg_type
    assert restored.request_id == original.request_id
    assert restored.data["method"] == original.data["method"]
    assert restored.data["path"] == original.data["path"]
