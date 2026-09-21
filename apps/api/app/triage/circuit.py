import time
from collections.abc import Callable
from threading import Lock
from typing import Literal

from app.triage.port import ProviderUnavailable

CircuitState = Literal["closed", "open", "half_open"]


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._lock = Lock()
        self._failures = 0
        self._opened_at: float | None = None
        self._probing = False

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state()

    def before_call(self) -> None:
        with self._lock:
            state = self._state()
            if state == "closed":
                return
            if state == "half_open" and not self._probing:
                self._probing = True
                return
            raise ProviderUnavailable(
                "Triage circuit is open", retry_after=self._remaining_cooldown()
            )

    def record_available(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._probing = False

    def record_unavailable(self) -> None:
        with self._lock:
            self._failures += 1
            if self._probing or self._failures >= self.failure_threshold:
                self._opened_at = self._clock()
            self._probing = False

    def _state(self) -> CircuitState:
        if self._opened_at is None:
            return "closed"
        if self._remaining_cooldown() > 0:
            return "open"
        return "half_open"

    def _remaining_cooldown(self) -> float:
        if self._opened_at is None:
            return 0.0
        return max(0.0, self._opened_at + self.cooldown_seconds - self._clock())
