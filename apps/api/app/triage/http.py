import time
from collections.abc import Callable
from dataclasses import dataclass
from secrets import SystemRandom

import httpx

from app.triage.port import MalformedResponse, ProviderRejected, ProviderUnavailable

TOO_MANY_REQUESTS = 429
DEFAULT_TIMEOUT = httpx.Timeout(connect=3.0, read=8.0, write=8.0, pool=8.0)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    deadline_seconds: float = 10.0
    base_delay_seconds: float = 0.2
    max_delay_seconds: float = 2.0

    def delay(self, attempt: int, error: ProviderUnavailable, jitter: Callable) -> float:
        if error.retry_after is not None:
            return error.retry_after
        return jitter(min(self.max_delay_seconds, self.base_delay_seconds * 2 ** (attempt - 1)))


def _full_jitter(cap: float) -> float:
    return SystemRandom().uniform(0, cap)


class HttpEvaluator:
    def __init__(
        self,
        url: str,
        api_key: str,
        label: str,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        retry: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        jitter: Callable[[float], float] = _full_jitter,
    ) -> None:
        self._url = url
        self._label = label
        self._timeout = timeout
        self._retry = retry or RetryPolicy()
        self._sleep = sleep
        self._clock = clock
        self._jitter = jitter
        self._client = httpx.Client(headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)

    @property
    def is_closed(self) -> bool:
        return self._client.is_closed

    def post(self, payload: dict) -> dict:
        deadline = self._clock() + self._retry.deadline_seconds
        attempt = 0
        while True:
            attempt += 1
            try:
                return self._attempt(payload, deadline - self._clock())
            except ProviderUnavailable as error:
                delay = self._retry.delay(attempt, error, self._jitter)
                if attempt >= self._retry.max_attempts or self._clock() + delay >= deadline:
                    raise
                self._sleep(delay)

    def _attempt(self, payload: dict, remaining: float) -> dict:
        try:
            response = self._client.post(
                self._url, json=payload, timeout=_bounded(self._timeout, remaining)
            )
        except httpx.HTTPError as error:
            raise ProviderUnavailable(f"Could not reach {self._label}: {error}") from error
        if response.is_error:
            raise self._status_error(response)
        try:
            body = response.json()
        except ValueError as error:
            raise MalformedResponse(f"Unexpected {self._label} response: not JSON") from error
        if not isinstance(body, dict):
            raise MalformedResponse(f"Unexpected {self._label} response: not an object")
        return body

    def close(self) -> None:
        self._client.close()

    def _status_error(self, response: httpx.Response) -> ProviderUnavailable | ProviderRejected:
        message = f"{self._label} returned {response.status_code}: {_error_message(response)}"
        if response.status_code == TOO_MANY_REQUESTS or response.is_server_error:
            return ProviderUnavailable(message, retry_after=_retry_after(response))
        return ProviderRejected(message)


def _bounded(timeout: httpx.Timeout, remaining: float) -> httpx.Timeout:
    remaining = max(remaining, 0.001)
    return httpx.Timeout(
        connect=min(timeout.connect or remaining, remaining),
        read=min(timeout.read or remaining, remaining),
        write=min(timeout.write or remaining, remaining),
        pool=min(timeout.pool or remaining, remaining),
    )


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        return None


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict):
        detail = body.get("error", body)
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("detail")
            if isinstance(message, str):
                return message
    return response.text[:200]
