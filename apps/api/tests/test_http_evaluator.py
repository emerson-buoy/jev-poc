import httpx
import pytest
import respx

from app.triage.http import HttpEvaluator
from app.triage.port import (
    MalformedResponse,
    ProviderRejected,
    ProviderUnavailable,
    TriageError,
)

URL = "https://example.test/v1/evaluate"


@pytest.fixture
def evaluator():
    evaluator = HttpEvaluator(url=URL, api_key="k", label="Example")
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
