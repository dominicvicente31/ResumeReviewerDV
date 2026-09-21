from collections import defaultdict
from datetime import datetime, timedelta, timezone


class _LoginTracker:
    """In-memory failed-login tracker. Resets on server restart — acceptable for single-instance."""

    def __init__(self) -> None:
        self._failures: dict[str, list[datetime]] = defaultdict(list)

    def _prune(self, email: str, window_minutes: int) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        self._failures[email] = [t for t in self._failures[email] if t > cutoff]

    def is_locked(self, email: str, max_attempts: int, window_minutes: int) -> bool:
        self._prune(email, window_minutes)
        return len(self._failures[email]) >= max_attempts

    def record_failure(self, email: str) -> None:
        self._failures[email].append(datetime.now(timezone.utc))

    def reset(self, email: str) -> None:
        self._failures.pop(email, None)


login_tracker = _LoginTracker()
