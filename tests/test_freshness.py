import pytest

from lib.scout.freshness import compute_freshness
from tests.conftest import TODAY


@pytest.mark.parametrize(
    ("deadline", "recurring", "expected"),
    [
        (None, True, "recurring"),
        ("2026-01-01", True, "recurring"),  # recurring wins over a past deadline
        (None, False, "unknown"),
        ("not-a-date", False, "unknown"),
        ("2026-05-31", False, "expired"),
        ("2026-06-01", False, "expiring_soon"),
        ("2026-06-15", False, "expiring_soon"),
        ("2026-06-16", False, "active"),
        ("2026-06-16T00:00:00", False, "active"),
    ],
)
def test_compute_freshness(deadline, recurring, expected):
    assert compute_freshness(deadline, recurring, today=TODAY) == expected
