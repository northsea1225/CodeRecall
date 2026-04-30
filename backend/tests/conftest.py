from __future__ import annotations

import pytest

from app.core.limiter import limiter


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """Default off: rate limiting must not interfere with existing test suite.

    The single rate-limit test opts back in via the ``rate_limiter_enabled`` fixture.
    """
    previous = limiter.enabled
    limiter.enabled = False
    limiter.reset()
    try:
        yield
    finally:
        limiter.reset()
        limiter.enabled = previous


@pytest.fixture
def rate_limiter_enabled():
    """Opt-in fixture for tests that need real rate-limit enforcement."""
    previous = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    try:
        yield limiter
    finally:
        limiter.reset()
        limiter.enabled = previous
