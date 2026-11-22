"""Clock helpers.

``datetime.utcnow()`` is deprecated (Python 3.12+). The database stores naive
UTC timestamps, so ``utcnow_naive`` keeps that exact format while using the
supported API; new code that doesn't touch stored values should use ``utcnow``.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Timezone-aware current time in UTC."""
    return datetime.now(UTC)


def utcnow_naive() -> datetime:
    """Current UTC time without tzinfo — matches timestamps already in the DB."""
    return utcnow().replace(tzinfo=None)
