"""Tests for webhook integrations."""

import pytest
import asyncio
from pytunnel.common.webhooks import WebhookManager, Webhook, WebhookEvent


def test_add_webhook():
    """Test adding a webhook."""
    manager = WebhookManager()

    webhook = manager.add_webhook(
        url="https://hooks.slack.com/services/test",
        events=["tunnel.started", "tunnel.stopped"],
        format="slack"
    )

    assert webhook.id is not None
    assert webhook.url == "https://hooks.slack.com/services/test"
    assert webhook.format == "slack"
    assert webhook.enabled


def test_invalid_url():
    """Test that invalid URLs are rejected."""
    manager = WebhookManager()

    # Localhost should be blocked
    with pytest.raises(ValueError):
        manager.add_webhook(
            url="http://localhost:8080/webhook",
            events=["tunnel.started"]
        )

    # Private IP should be blocked
    with pytest.raises(ValueError):
        manager.add_webhook(
            url="http://192.168.1.1/webhook",
            events=["tunnel.started"]
        )

    # Cloud metadata should be blocked
    with pytest.raises(ValueError):
        manager.add_webhook(
            url="http://169.254.169.254/webhook",
            events=["tunnel.started"]
        )


def test_event_matching():
    """Test event pattern matching."""
    webhook = Webhook(
        id="test",
        url="https://example.com/webhook",
        events=["tunnel.started", "request.*"]
    )

    # Exact match
    assert webhook.matches_event("tunnel.started")

    # Wildcard match
    assert webhook.matches_event("request.error")
    assert webhook.matches_event("request.success")

    # No match
    assert not webhook.matches_event("share.created")


def test_remove_webhook():
    """Test removing a webhook."""
    manager = WebhookManager()

    webhook = manager.add_webhook(
        url="https://example.com/webhook",
        events=["tunnel.started"]
    )

    assert manager.remove_webhook(webhook.id)
    assert manager.get_webhook(webhook.id) is None


def test_format_slack_payload():
    """Test Slack payload formatting."""
    manager = WebhookManager()

    payload = manager._format_slack(
        "tunnel.started",
        {"client_id": "abc123", "url": "https://tunnel.example.com"}
    )

    assert "attachments" in payload
    assert len(payload["attachments"]) > 0
    assert "color" in payload["attachments"][0]
    assert "fields" in payload["attachments"][0]


def test_format_discord_payload():
    """Test Discord payload formatting."""
    manager = WebhookManager()

    payload = manager._format_discord(
        "tunnel.error",
        {"client_id": "abc123", "error": "Connection failed"}
    )

    assert "embeds" in payload
    assert len(payload["embeds"]) > 0
    assert "color" in payload["embeds"][0]
    assert "fields" in payload["embeds"][0]


def test_hmac_signature():
    """Test HMAC signature generation."""
    manager = WebhookManager()

    payload = '{"test": "data"}'
    secret = "my-secret-key"

    signature = manager._sign_payload(payload, secret)

    assert signature.startswith("sha256=")
    assert len(signature) > 10


def test_rate_limiting():
    """Test webhook rate limiting."""
    manager = WebhookManager()
    manager.max_webhooks_per_minute = 5

    webhook_id = "test-webhook"

    # First 5 should succeed
    for _ in range(5):
        assert manager._check_rate_limit(webhook_id)

    # 6th should fail
    assert not manager._check_rate_limit(webhook_id)


@pytest.mark.asyncio
async def test_trigger_webhooks():
    """Test triggering webhooks."""
    manager = WebhookManager()

    # Add a webhook (will fail to send but that's okay for test)
    webhook = manager.add_webhook(
        url="https://httpbin.org/post",
        events=["tunnel.*"],
        format="generic"
    )

    # Trigger event
    await manager.trigger(
        "tunnel.started",
        {"client_id": "abc123"}
    )

    # Check that success/failure counts were updated
    assert webhook.success_count + webhook.failure_count > 0


def test_webhook_stats():
    """Test getting webhook statistics."""
    manager = WebhookManager()

    webhook = manager.add_webhook(
        url="https://example.com/webhook",
        events=["tunnel.started"]
    )

    stats = manager.get_stats(webhook.id)

    assert stats is not None
    assert stats['id'] == webhook.id
    assert stats['url'] == webhook.url
    assert 'success_count' in stats
    assert 'failure_count' in stats
