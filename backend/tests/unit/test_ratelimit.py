import pytest

from app.ratelimit.limiter import TokenBucketLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_burst_then_blocked_with_retry_after():
    clock = FakeClock()
    limiter = TokenBucketLimiter(per_minute=60, burst=3, clock=clock)  # 1 token a second
    assert [limiter.try_acquire("a").allowed for _ in range(3)] == [True, True, True]
    blocked = limiter.try_acquire("a")
    assert not blocked.allowed and blocked.retry_after == 1


def test_tokens_refill_over_time_up_to_the_burst():
    clock = FakeClock()
    limiter = TokenBucketLimiter(per_minute=60, burst=3, clock=clock)
    for _ in range(3):
        limiter.try_acquire("a")
    clock.now += 2
    assert limiter.try_acquire("a").allowed
    assert limiter.try_acquire("a").allowed
    assert not limiter.try_acquire("a").allowed
    clock.now += 3600  # a long pause refills to the burst, not beyond
    assert sum(limiter.try_acquire("a").allowed for _ in range(10)) == 3


def test_retry_after_reflects_a_slow_rate():
    clock = FakeClock()
    limiter = TokenBucketLimiter(per_minute=6, burst=1, clock=clock)  # one every 10 s
    limiter.try_acquire("a")
    assert limiter.try_acquire("a").retry_after == 10


def test_keys_are_independent():
    limiter = TokenBucketLimiter(per_minute=60, burst=1, clock=FakeClock())
    assert limiter.try_acquire("a").allowed
    assert not limiter.try_acquire("a").allowed
    assert limiter.try_acquire("b").allowed


def test_peek_does_not_consume():
    limiter = TokenBucketLimiter(per_minute=60, burst=1, clock=FakeClock())
    for _ in range(5):
        assert limiter.peek("a").allowed
    assert limiter.try_acquire("a").allowed
    assert not limiter.peek("a").allowed


def test_memory_stays_bounded():
    clock = FakeClock()
    limiter = TokenBucketLimiter(per_minute=60, burst=5, clock=clock, max_entries=100)
    for i in range(1000):
        limiter.try_acquire(f"ip-{i}")
        clock.now += 0.001
    assert len(limiter) <= 101


@pytest.mark.parametrize(("per_minute", "burst"), [(0, 1), (10, 0)])
def test_rejects_nonsense_configuration(per_minute, burst):
    with pytest.raises(ValueError):
        TokenBucketLimiter(per_minute, burst)
