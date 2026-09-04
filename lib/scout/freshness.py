from datetime import date

# Deadlines this close or closer are worth calling out separately from
# "active" — same bucket as far as filtering goes, just a stronger signal.
EXPIRING_SOON_DAYS = 14

FRESHNESS_VALUES = ("recurring", "expired", "expiring_soon", "active", "unknown")


def compute_freshness(deadline_at: str | None, is_recurring: bool = False) -> str:
    """Derive a freshness label from a deadline, computed fresh on every read.

    Deliberately not stored: a persisted status would need to be kept in sync
    with the passage of time by something re-touching every row, which is
    exactly the kind of upkeep that let stale opportunities pass unnoticed
    before. Computing it from `deadline_at` + `is_recurring` at read time means
    it can never go stale itself.

    - "recurring"      — flagged as an evergreen/rolling program; always active
    - "expired"        — deadline has passed
    - "expiring_soon"  — deadline within EXPIRING_SOON_DAYS
    - "active"         — deadline further out than that
    - "unknown"        — no deadline could be extracted, not flagged recurring
    """
    if is_recurring:
        return "recurring"
    if not deadline_at:
        return "unknown"
    try:
        deadline = date.fromisoformat(str(deadline_at)[:10])
    except ValueError:
        return "unknown"

    days_out = (deadline - date.today()).days
    if days_out < 0:
        return "expired"
    if days_out <= EXPIRING_SOON_DAYS:
        return "expiring_soon"
    return "active"
