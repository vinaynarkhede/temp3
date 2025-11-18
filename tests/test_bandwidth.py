"""Tests for bandwidth limiting."""

import pytest
import asyncio
import time
from pytunnel.common.bandwidth import (
    TokenBucket, BandwidthLimiter, RequestRateLimiter
)


def test_token_bucket_consume():
    """Test token bucket consumption."""
    bucket = TokenBucket(rate=100, capacity=100)

    # Should be able to consume tokens
    assert bucket.consume(50)
    assert bucket.consume(50)

    # Should fail when exceeding capacity
    assert not bucket.consume(10)


def test_token_bucket_refill():
    """Test token bucket refilling."""
    bucket = TokenBucket(rate=100, capacity=100)

    # Consume all tokens
    assert bucket.consume(100)
    assert not bucket.consume(10)

    # Wait for refill (0.5 seconds should add 50 tokens at 100/sec)
    time.sleep(0.5)

    # Should now be able to consume again
    assert bucket.consume(40)


@pytest.mark.asyncio
async def test_token_bucket_async():
    """Test async token bucket consumption."""
    bucket = TokenBucket(rate=100, capacity=100)

    # Consume all tokens
    assert bucket.consume(100)

    # Should wait and then succeed
    result = await bucket.consume_async(50, timeout=1.0)
    assert result


@pytest.mark.asyncio
async def test_bandwidth_limiter():
    """Test bandwidth limiter."""
    limiter = BandwidthLimiter()

    # Set limit: 1000 bytes/sec upload, 2000 bytes/sec download
    limiter.set_client_limit("client1", upload_limit=1000, download_limit=2000)

    # Should be able to acquire within limits
    assert await limiter.acquire_upload("client1", 500, timeout=1.0)
    assert await limiter.acquire_download("client1", 1000, timeout=1.0)


@pytest.mark.asyncio
async def test_bandwidth_limiter_global():
    """Test global bandwidth limiting."""
    limiter = BandwidthLimiter()

    # Set global limit
    limiter.set_global_limit(upload_limit=1000, download_limit=2000)

    # Should apply to all clients
    assert await limiter.acquire_upload("client1", 500, timeout=1.0)
    assert await limiter.acquire_upload("client2", 500, timeout=1.0)

    # Should fail when exceeding global limit
    result = await limiter.acquire_upload("client3", 100, timeout=0.1)
    assert not result


@pytest.mark.asyncio
async def test_bandwidth_limiter_remove():
    """Test removing client limit."""
    limiter = BandwidthLimiter()

    limiter.set_client_limit("client1", upload_limit=100, download_limit=200)
    limiter.remove_client_limit("client1")

    # Should succeed without limits
    assert await limiter.acquire_upload("client1", 10000, timeout=0.1)


def test_request_rate_limiter():
    """Test request rate limiting."""
    limiter = RequestRateLimiter(max_requests=5, window_seconds=1)

    # First 5 requests should succeed
    for _ in range(5):
        assert limiter.is_allowed("client1")

    # 6th request should fail
    assert not limiter.is_allowed("client1")

    # Wait for window to pass
    time.sleep(1.1)

    # Should allow again
    assert limiter.is_allowed("client1")


def test_request_rate_limiter_multiple_clients():
    """Test rate limiting for multiple clients."""
    limiter = RequestRateLimiter(max_requests=5, window_seconds=1)

    # Each client should have independent limits
    for _ in range(5):
        assert limiter.is_allowed("client1")
        assert limiter.is_allowed("client2")

    # Both should be rate limited
    assert not limiter.is_allowed("client1")
    assert not limiter.is_allowed("client2")


def test_request_rate_limiter_remaining():
    """Test getting remaining requests."""
    limiter = RequestRateLimiter(max_requests=10, window_seconds=60)

    # Check initial remaining
    assert limiter.get_remaining("client1") == 10

    # Use some requests
    for _ in range(3):
        limiter.is_allowed("client1")

    assert limiter.get_remaining("client1") == 7


def test_request_rate_limiter_reset():
    """Test resetting rate limit."""
    limiter = RequestRateLimiter(max_requests=5, window_seconds=1)

    # Use up requests
    for _ in range(5):
        limiter.is_allowed("client1")

    assert not limiter.is_allowed("client1")

    # Reset
    limiter.reset("client1")

    # Should allow again
    assert limiter.is_allowed("client1")
