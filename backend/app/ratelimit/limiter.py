"""Rate limiting: a token bucket per key (a user id, or a client IP for failed sign-ins).

In-memory, so limits are per process. That is correct for a single instance (the free-tier
setup). With several instances, swap in a shared store (Redis) behind the same interface.
"""

import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int = 0  # whole seconds until one more request would be allowed


class RateLimiter(Protocol):
    def peek(self, key: str) -> Decision: ...
    def try_acquire(self, key: str) -> Decision: ...


class TokenBucketLimiter:
    """`burst` requests at once, refilling at `per_minute` requests a minute."""

    def __init__(
        self,
        per_minute: float,
        burst: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_entries: int = 10_000,
    ) -> None:
        if per_minute <= 0 or burst < 1:
            raise ValueError("per_minute must be > 0 and burst >= 1")
        self.rate = per_minute / 60.0  # tokens per second
        self.burst = float(burst)
        self.clock = clock
        self.max_entries = max_entries
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last update)
        self._lock = threading.Lock()

    def _tokens(self, key: str, now: float) -> float:
        tokens, last = self._buckets.get(key, (self.burst, now))
        return min(self.burst, tokens + (now - last) * self.rate)

    def _decision(self, tokens: float) -> Decision:
        if tokens >= 1:
            return Decision(True)
        return Decision(False, max(1, math.ceil((1 - tokens) / self.rate)))

    def peek(self, key: str) -> Decision:
        """Would a request be allowed right now? Does not use up a token."""
        with self._lock:
            return self._decision(self._tokens(key, self.clock()))

    def try_acquire(self, key: str) -> Decision:
        with self._lock:
            now = self.clock()
            tokens = self._tokens(key, now)
            decision = self._decision(tokens)
            self._buckets[key] = (tokens - 1 if decision.allowed else tokens, now)
            if len(self._buckets) > self.max_entries:
                self._evict(now)
            return decision

    def _evict(self, now: float) -> None:
        """Drop full (idle) buckets first: forgetting them changes nothing. If every bucket is
        busy, drop the least recently used ones to keep memory bounded."""
        full = [k for k in self._buckets if self._tokens(k, now) >= self.burst]
        for k in full:
            del self._buckets[k]
        overflow = len(self._buckets) - self.max_entries
        if overflow > 0:
            oldest = sorted(self._buckets, key=lambda k: self._buckets[k][1])[:overflow]
            for k in oldest:
                del self._buckets[k]

    def __len__(self) -> int:
        return len(self._buckets)
