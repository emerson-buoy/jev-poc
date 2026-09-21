import httpx
import pytest
import respx

from app.triage.http import HttpEvaluator, RetryPolicy
from app.triage.port import (
    MalformedResponse,
    ProviderRejected,
    ProviderUnavailable,
    TriageError,
)

URL = "https://example.test/v1/evaluate"


@pytest.fixture
def evaluator():
    evaluator = HttpEvaluator(
        url=URL, api_key="k", label="Example", retry=RetryPolicy(max_attempts=1)
    )
    yield evaluator
    evaluator.close()


@respx.mock
def test_posts_json_with_bearer_and_returns_body(evaluator):
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"answers": {}}))
    assert evaluator.post({"model": "m"}) == {"answers": {}}
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer k"
    assert httpx.Response(200, content=request.content).json() == {"model": "m"}


@respx.mock
def test_network_error_names_the_service(evaluator):
    respx.post(URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(ProviderUnavailable, match="Could not reach Example"):
        evaluator.post({})


@respx.mock
def test_timeout_is_unavailable(evaluator):
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(ProviderUnavailable):
        evaluator.post({})


@respx.mock
@pytest.mark.parametrize("status", [429, 500, 502, 503, 529])
def test_overload_and_server_errors_are_unavailable(evaluator, status):
    respx.post(URL).mock(return_value=httpx.Response(status, text="later"))
    with pytest.raises(ProviderUnavailable) as info:
        evaluator.post({})
    assert info.value.retry_after is None


@respx.mock
def test_retry_after_seconds_is_kept(evaluator):
    respx.post(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "7"}))
    with pytest.raises(ProviderUnavailable) as info:
        evaluator.post({})
    assert info.value.retry_after == 7.0


@respx.mock
def test_unparseable_retry_after_is_none(evaluator):
    respx.post(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "soon"}))
    with pytest.raises(ProviderUnavailable) as info:
        evaluator.post({})
    assert info.value.retry_after is None


@respx.mock
@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_client_errors_are_rejections(evaluator, status):
    respx.post(URL).mock(return_value=httpx.Response(status, json={"message": "no"}))
    with pytest.raises(ProviderRejected):
        evaluator.post({})


@respx.mock
@pytest.mark.parametrize(
    "body",
    [
        {"message": "Invalid API key"},
        {"detail": "Invalid API key"},
        {"error": {"message": "Invalid API key"}},
    ],
)
def test_http_error_carries_status_and_message(evaluator, body):
    respx.post(URL).mock(return_value=httpx.Response(401, json=body))
    with pytest.raises(TriageError, match="Example returned 401: Invalid API key"):
        evaluator.post({})


@respx.mock
def test_http_error_without_json_falls_back_to_text(evaluator):
    respx.post(URL).mock(return_value=httpx.Response(502, text="Bad gateway"))
    with pytest.raises(TriageError, match="Example returned 502: Bad gateway"):
        evaluator.post({})


@respx.mock
def test_non_json_success_body_is_a_triage_error(evaluator):
    respx.post(URL).mock(return_value=httpx.Response(200, text="<html>"))
    with pytest.raises(MalformedResponse, match="Unexpected Example response"):
        evaluator.post({})


def test_close_closes_the_client():
    evaluator = HttpEvaluator(url=URL, api_key="k", label="Example")
    assert not evaluator.is_closed
    evaluator.close()
    assert evaluator.is_closed


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def retrying(time: FakeTime, **policy) -> HttpEvaluator:
    return HttpEvaluator(
        url=URL,
        api_key="k",
        label="Example",
        retry=RetryPolicy(**{"max_attempts": 3, "deadline_seconds": 10.0, **policy}),
        sleep=time.sleep,
        clock=time.clock,
        jitter=lambda cap: cap,
    )


@respx.mock
def test_retries_unavailable_then_succeeds():
    time = FakeTime()
    route = respx.post(URL).mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"answers": {}})]
    )
    assert retrying(time).post({}) == {"answers": {}}
    assert route.call_count == 2
    assert len(time.sleeps) == 1


@respx.mock
def test_backoff_is_exponential_up_to_the_cap():
    time = FakeTime()
    respx.post(URL).mock(return_value=httpx.Response(503))
    policy = {"max_attempts": 4, "base_delay_seconds": 0.5, "max_delay_seconds": 1.5}
    with pytest.raises(ProviderUnavailable):
        retrying(time, **policy).post({})
    assert time.sleeps == [0.5, 1.0, 1.5]


@respx.mock
def test_gives_up_after_max_attempts():
    time = FakeTime()
    route = respx.post(URL).mock(return_value=httpx.Response(529))
    with pytest.raises(ProviderUnavailable, match="529"):
        retrying(time).post({})
    assert route.call_count == 3
    assert len(time.sleeps) == 2


@respx.mock
def test_retry_after_sets_the_delay():
    time = FakeTime()
    respx.post(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3"}),
            httpx.Response(200, json={}),
        ]
    )
    retrying(time).post({})
    assert time.sleeps == [3.0]


@respx.mock
def test_does_not_sleep_past_the_deadline():
    time = FakeTime()
    route = respx.post(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "20"}))
    with pytest.raises(ProviderUnavailable, match="429"):
        retrying(time).post({})
    assert route.call_count == 1
    assert time.sleeps == []


@respx.mock
def test_rejections_are_not_retried():
    time = FakeTime()
    route = respx.post(URL).mock(return_value=httpx.Response(401, json={"message": "no"}))
    with pytest.raises(ProviderRejected):
        retrying(time).post({})
    assert route.call_count == 1


@respx.mock
def test_malformed_success_is_not_retried():
    time = FakeTime()
    route = respx.post(URL).mock(return_value=httpx.Response(200, text="<html>"))
    with pytest.raises(MalformedResponse):
        retrying(time).post({})
    assert route.call_count == 1


@respx.mock
def test_each_attempt_is_bounded_by_the_remaining_budget():
    time = FakeTime()

    def slow_failure(request):
        time.now += 6.0
        return httpx.Response(503)

    route = respx.post(URL).mock(side_effect=slow_failure)
    evaluator = HttpEvaluator(
        url=URL,
        api_key="k",
        label="Example",
        timeout=httpx.Timeout(connect=3.0, read=8.0, write=8.0, pool=8.0),
        retry=RetryPolicy(max_attempts=3, deadline_seconds=10.0, base_delay_seconds=0.0),
        sleep=time.sleep,
        clock=time.clock,
        jitter=lambda cap: cap,
    )
    with pytest.raises(ProviderUnavailable):
        evaluator.post({})
    timeouts = [call.request.extensions["timeout"]["read"] for call in route.calls]
    assert timeouts == [8.0, 4.0]
