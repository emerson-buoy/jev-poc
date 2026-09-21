import pytest

from app.triage.circuit import CircuitBreaker
from app.triage.port import ProviderUnavailable


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def breaker(clock):
    return CircuitBreaker(failure_threshold=3, cooldown_seconds=30.0, clock=clock)


def trip(breaker: CircuitBreaker, times: int = 3) -> None:
    for _ in range(times):
        breaker.before_call()
        breaker.record_unavailable()


def test_starts_closed(breaker):
    assert breaker.state == "closed"
    breaker.before_call()


def test_stays_closed_below_the_threshold(breaker):
    trip(breaker, 2)
    assert breaker.state == "closed"


def test_opens_at_the_threshold(breaker):
    trip(breaker)
    assert breaker.state == "open"


def test_open_rejects_with_the_remaining_cooldown(breaker, clock):
    trip(breaker)
    clock.now += 10
    with pytest.raises(ProviderUnavailable) as info:
        breaker.before_call()
    assert info.value.retry_after == 20.0


def test_available_outcome_resets_the_count(breaker):
    trip(breaker, 2)
    breaker.before_call()
    breaker.record_available()
    trip(breaker, 2)
    assert breaker.state == "closed"


def test_half_open_after_the_cooldown_lets_one_probe_through(breaker, clock):
    trip(breaker)
    clock.now += 30
    assert breaker.state == "half_open"
    breaker.before_call()
    with pytest.raises(ProviderUnavailable):
        breaker.before_call()


def test_probe_success_closes_the_circuit(breaker, clock):
    trip(breaker)
    clock.now += 30
    breaker.before_call()
    breaker.record_available()
    assert breaker.state == "closed"
    trip(breaker, 2)
    assert breaker.state == "closed"


def test_probe_failure_reopens_with_a_fresh_cooldown(breaker, clock):
    trip(breaker)
    clock.now += 30
    breaker.before_call()
    breaker.record_unavailable()
    assert breaker.state == "open"
    with pytest.raises(ProviderUnavailable) as info:
        breaker.before_call()
    assert info.value.retry_after == 30.0


def test_defaults():
    breaker = CircuitBreaker()
    assert breaker.failure_threshold == 5
    assert breaker.cooldown_seconds == 30.0
