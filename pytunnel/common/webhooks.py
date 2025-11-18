"""Webhook integration system for notifications."""

import asyncio
import hmac
import hashlib
import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
from urllib.parse import urlparse


class WebhookEvent(Enum):
    """Webhook event types."""
    TUNNEL_STARTED = "tunnel.started"
    TUNNEL_STOPPED = "tunnel.stopped"
    TUNNEL_ERROR = "tunnel.error"
    REQUEST_ERROR = "request.error"
    SHARE_CREATED = "share.created"
    SHARE_ACCESSED = "share.accessed"
    AUTH_FAILED = "auth.failed"
    RATE_LIMITED = "rate.limited"


class WebhookFormat(Enum):
    """Webhook payload formats."""
    GENERIC = "generic"
    SLACK = "slack"
    DISCORD = "discord"
    PAGERDUTY = "pagerduty"


@dataclass
class Webhook:
    """Webhook configuration."""
    id: str
    url: str
    events: List[str]  # Event patterns like "tunnel.*" or "request.error"
    format: str = "generic"
    secret: Optional[str] = None
    enabled: bool = True
    created_at: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_triggered: Optional[float] = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

    def matches_event(self, event: str) -> bool:
        """Check if webhook should trigger for event."""
        for pattern in self.events:
            if pattern == event:
                return True
            # Support wildcard matching
            if pattern.endswith('.*'):
                prefix = pattern[:-2]
                if event.startswith(prefix):
                    return True
        return False


class WebhookManager:
    """Manages webhooks and delivery."""

    def __init__(self):
        self.webhooks: Dict[str, Webhook] = {}
        self.rate_limits: Dict[str, List[float]] = {}  # webhook_id -> timestamps
        self.max_webhooks_per_minute = 100

    def add_webhook(
        self,
        url: str,
        events: List[str],
        format: str = "generic",
        secret: Optional[str] = None
    ) -> Webhook:
        """Add a new webhook."""
        # Validate URL
        if not self._is_valid_url(url):
            raise ValueError("Invalid webhook URL")

        # Generate ID
        webhook_id = hashlib.sha256(
            f"{url}{time.time()}".encode()
        ).hexdigest()[:16]

        webhook = Webhook(
            id=webhook_id,
            url=url,
            events=events,
            format=format,
            secret=secret
        )

        self.webhooks[webhook_id] = webhook
        return webhook

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL to prevent SSRF attacks."""
        try:
            parsed = urlparse(url)

            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False

            # Only allow http and https
            if parsed.scheme not in ['http', 'https']:
                return False

            # Block localhost and private IPs
            hostname = parsed.hostname
            if not hostname:
                return False

            # Block localhost variants
            if hostname.lower() in ['localhost', '127.0.0.1', '::1']:
                return False

            # Block private IP ranges
            if hostname.startswith('10.'):
                return False
            if hostname.startswith('172.') and 16 <= int(hostname.split('.')[1]) <= 31:
                return False
            if hostname.startswith('192.168.'):
                return False

            # Block cloud metadata endpoints
            if hostname in ['169.254.169.254', 'metadata.google.internal']:
                return False

            return True

        except Exception:
            return False

    def remove_webhook(self, webhook_id: str) -> bool:
        """Remove a webhook."""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            return True
        return False

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook by ID."""
        return self.webhooks.get(webhook_id)

    def list_webhooks(self) -> List[Webhook]:
        """List all webhooks."""
        return list(self.webhooks.values())

    def _check_rate_limit(self, webhook_id: str) -> bool:
        """Check if webhook is rate limited."""
        now = time.time()

        if webhook_id not in self.rate_limits:
            self.rate_limits[webhook_id] = []

        # Clean up old timestamps (older than 1 minute)
        self.rate_limits[webhook_id] = [
            t for t in self.rate_limits[webhook_id]
            if now - t < 60
        ]

        # Check limit
        if len(self.rate_limits[webhook_id]) >= self.max_webhooks_per_minute:
            return False

        # Add current timestamp
        self.rate_limits[webhook_id].append(now)
        return True

    def _sign_payload(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for payload."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def _format_generic(self, event: str, data: Dict[str, Any]) -> Dict:
        """Format payload for generic webhook."""
        return {
            "event": event,
            "timestamp": time.time(),
            "data": data
        }

    def _format_slack(self, event: str, data: Dict[str, Any]) -> Dict:
        """Format payload for Slack."""
        # Map events to emoji and colors
        event_config = {
            "tunnel.started": {"emoji": "🚀", "color": "#36a64f"},
            "tunnel.stopped": {"emoji": "⏹️", "color": "#ff9900"},
            "tunnel.error": {"emoji": "❌", "color": "#ff0000"},
            "request.error": {"emoji": "⚠️", "color": "#ffcc00"},
            "share.created": {"emoji": "🔗", "color": "#6f42c1"},
            "share.accessed": {"emoji": "👁️", "color": "#17a2b8"},
        }

        config = event_config.get(event, {"emoji": "ℹ️", "color": "#808080"})

        # Build message
        title = f"{config['emoji']} {event.replace('.', ' ').title()}"

        fields = []
        for key, value in data.items():
            fields.append({
                "title": key.replace('_', ' ').title(),
                "value": str(value),
                "short": True
            })

        return {
            "attachments": [{
                "fallback": f"{title}: {json.dumps(data)}",
                "color": config["color"],
                "title": title,
                "fields": fields,
                "footer": "PyTunnel",
                "ts": int(time.time())
            }]
        }

    def _format_discord(self, event: str, data: Dict[str, Any]) -> Dict:
        """Format payload for Discord."""
        # Map events to colors
        colors = {
            "tunnel.started": 0x36a64f,  # Green
            "tunnel.stopped": 0xff9900,  # Orange
            "tunnel.error": 0xff0000,    # Red
            "request.error": 0xffcc00,   # Yellow
            "share.created": 0x6f42c1,   # Purple
            "share.accessed": 0x17a2b8,  # Blue
        }

        color = colors.get(event, 0x808080)

        # Build fields
        fields = []
        for key, value in data.items():
            fields.append({
                "name": key.replace('_', ' ').title(),
                "value": str(value),
                "inline": True
            })

        return {
            "embeds": [{
                "title": event.replace('.', ' ').title(),
                "color": color,
                "fields": fields,
                "footer": {
                    "text": "PyTunnel"
                },
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }]
        }

    def _format_pagerduty(self, event: str, data: Dict[str, Any]) -> Dict:
        """Format payload for PagerDuty."""
        # PagerDuty Events API v2 format
        severity = "error" if "error" in event else "info"

        return {
            "routing_key": data.get("routing_key", ""),
            "event_action": "trigger",
            "payload": {
                "summary": f"PyTunnel: {event}",
                "severity": severity,
                "source": "pytunnel",
                "custom_details": data
            }
        }

    async def trigger(self, event: str, data: Dict[str, Any]):
        """Trigger webhooks for an event."""
        # Find matching webhooks
        matching_webhooks = [
            webhook for webhook in self.webhooks.values()
            if webhook.enabled and webhook.matches_event(event)
        ]

        # Trigger all matching webhooks concurrently
        tasks = [
            self._send_webhook(webhook, event, data)
            for webhook in matching_webhooks
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_webhook(self, webhook: Webhook, event: str, data: Dict[str, Any]):
        """Send a single webhook."""
        # Check rate limit
        if not self._check_rate_limit(webhook.id):
            return

        # Format payload based on webhook format
        formatters = {
            "slack": self._format_slack,
            "discord": self._format_discord,
            "pagerduty": self._format_pagerduty,
            "generic": self._format_generic,
        }

        formatter = formatters.get(webhook.format, self._format_generic)
        payload = formatter(event, data)
        payload_str = json.dumps(payload)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PyTunnel-Webhook/1.0"
        }

        # Add signature if secret provided
        if webhook.secret:
            headers["X-Webhook-Signature"] = self._sign_payload(payload_str, webhook.secret)

        # Send webhook with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook.url,
                        data=payload_str,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status < 400:
                            # Success
                            webhook.success_count += 1
                            webhook.last_triggered = time.time()
                            return

                        # Server error, retry
                        if response.status >= 500 and attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue

                        # Client error, don't retry
                        webhook.failure_count += 1
                        return

            except asyncio.TimeoutError:
                webhook.failure_count += 1
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return

            except Exception as e:
                webhook.failure_count += 1
                return

    async def test_webhook(self, webhook_id: str) -> tuple[bool, Optional[str]]:
        """Test a webhook by sending a test event."""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False, "Webhook not found"

        test_data = {
            "message": "This is a test webhook from PyTunnel",
            "timestamp": time.time()
        }

        try:
            await self._send_webhook(webhook, "test", test_data)
            return True, None
        except Exception as e:
            return False, str(e)

    def get_stats(self, webhook_id: str) -> Optional[Dict]:
        """Get statistics for a webhook."""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None

        return {
            "id": webhook.id,
            "url": webhook.url,
            "enabled": webhook.enabled,
            "success_count": webhook.success_count,
            "failure_count": webhook.failure_count,
            "last_triggered": webhook.last_triggered,
            "created_at": webhook.created_at
        }


# Global instance
_webhook_manager = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager instance."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager
