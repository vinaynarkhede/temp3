"""Bandwidth limiting and rate limiting."""

import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class BandwidthLimit:
    """Bandwidth limit configuration."""
    bytes_per_second: int
    burst_size: int = 0

    def __post_init__(self):
        if self.burst_size == 0:
            self.burst_size = self.bytes_per_second


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, rate: float, capacity: float):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, tokens: float) -> bool:
        """Try to consume tokens. Returns True if successful."""
        self._add_tokens()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    async def consume_async(self, tokens: float, timeout: float = 10.0) -> bool:
        """
        Async consume with waiting.

        Waits until tokens are available or timeout is reached.
        """
        start_time = time.time()

        while True:
            if self.consume(tokens):
                return True

            # Calculate wait time
            if self.tokens < tokens:
                wait_time = (tokens - self.tokens) / self.rate
                wait_time = min(wait_time, 0.1)  # Max 100ms wait per iteration

                if time.time() - start_time + wait_time > timeout:
                    return False

                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(0.01)

    def _add_tokens(self):
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )
        self.last_update = now

    def get_available_tokens(self) -> float:
        """Get number of available tokens."""
        self._add_tokens()
        return self.tokens


class BandwidthLimiter:
    """Manages bandwidth limits for multiple clients."""

    def __init__(self):
        self.client_limits: Dict[str, BandwidthLimit] = {}
        self.client_buckets: Dict[str, tuple] = {}  # (upload_bucket, download_bucket)
        self.global_limit: Optional[BandwidthLimit] = None
        self.global_bucket: Optional[tuple] = None

    def set_client_limit(
        self,
        client_id: str,
        upload_limit: int,
        download_limit: int,
        burst_size: Optional[int] = None
    ):
        """
        Set bandwidth limit for a client.

        Args:
            client_id: Client identifier
            upload_limit: Upload bytes per second
            download_limit: Download bytes per second
            burst_size: Optional burst size (defaults to rate)
        """
        burst = burst_size or max(upload_limit, download_limit)

        upload_bucket = TokenBucket(upload_limit, burst)
        download_bucket = TokenBucket(download_limit, burst)

        self.client_buckets[client_id] = (upload_bucket, download_bucket)
        self.client_limits[client_id] = BandwidthLimit(
            bytes_per_second=max(upload_limit, download_limit),
            burst_size=burst
        )

    def set_global_limit(
        self,
        upload_limit: int,
        download_limit: int,
        burst_size: Optional[int] = None
    ):
        """Set global bandwidth limit."""
        burst = burst_size or max(upload_limit, download_limit)

        upload_bucket = TokenBucket(upload_limit, burst)
        download_bucket = TokenBucket(download_limit, burst)

        self.global_bucket = (upload_bucket, download_bucket)
        self.global_limit = BandwidthLimit(
            bytes_per_second=max(upload_limit, download_limit),
            burst_size=burst
        )

    def remove_client_limit(self, client_id: str):
        """Remove bandwidth limit for a client."""
        if client_id in self.client_buckets:
            del self.client_buckets[client_id]
        if client_id in self.client_limits:
            del self.client_limits[client_id]

    async def acquire_upload(
        self,
        client_id: str,
        size: int,
        timeout: float = 10.0
    ) -> bool:
        """
        Acquire tokens for upload.

        Returns True if allowed, False if rate limited.
        """
        # Check client limit
        if client_id in self.client_buckets:
            upload_bucket, _ = self.client_buckets[client_id]
            if not await upload_bucket.consume_async(size, timeout):
                return False

        # Check global limit
        if self.global_bucket:
            upload_bucket, _ = self.global_bucket
            if not await upload_bucket.consume_async(size, timeout):
                return False

        return True

    async def acquire_download(
        self,
        client_id: str,
        size: int,
        timeout: float = 10.0
    ) -> bool:
        """
        Acquire tokens for download.

        Returns True if allowed, False if rate limited.
        """
        # Check client limit
        if client_id in self.client_buckets:
            _, download_bucket = self.client_buckets[client_id]
            if not await download_bucket.consume_async(size, timeout):
                return False

        # Check global limit
        if self.global_bucket:
            _, download_bucket = self.global_bucket
            if not await download_bucket.consume_async(size, timeout):
                return False

        return True

    def get_client_stats(self, client_id: str) -> Dict[str, float]:
        """Get bandwidth statistics for a client."""
        if client_id not in self.client_buckets:
            return {}

        upload_bucket, download_bucket = self.client_buckets[client_id]

        return {
            'upload_available': upload_bucket.get_available_tokens(),
            'upload_capacity': upload_bucket.capacity,
            'download_available': download_bucket.get_available_tokens(),
            'download_capacity': download_bucket.capacity,
        }


class RequestRateLimiter:
    """Rate limiter for number of requests per time window."""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client."""
        now = time.time()

        if client_id not in self.requests:
            self.requests[client_id] = deque()

        # Remove old requests outside the window
        request_times = self.requests[client_id]
        while request_times and request_times[0] < now - self.window_seconds:
            request_times.popleft()

        # Check if limit exceeded
        if len(request_times) >= self.max_requests:
            return False

        # Add current request
        request_times.append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        if client_id not in self.requests:
            return self.max_requests

        now = time.time()
        request_times = self.requests[client_id]

        # Count requests in current window
        count = sum(1 for t in request_times if t >= now - self.window_seconds)
        return max(0, self.max_requests - count)

    def reset(self, client_id: str):
        """Reset rate limit for client."""
        if client_id in self.requests:
            del self.requests[client_id]


# Global instances
_bandwidth_limiter = None
_rate_limiter = None


def get_bandwidth_limiter() -> BandwidthLimiter:
    """Get the global bandwidth limiter instance."""
    global _bandwidth_limiter
    if _bandwidth_limiter is None:
        _bandwidth_limiter = BandwidthLimiter()
    return _bandwidth_limiter


def get_rate_limiter(max_requests: int = 100, window_seconds: int = 60) -> RequestRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RequestRateLimiter(max_requests, window_seconds)
    return _rate_limiter
