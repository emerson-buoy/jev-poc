import httpx
import pytest
import respx

from app.triage.http import HttpEvaluator
from app.triage.port import TriageError

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
    with pytest.raises(TriageError, match="Could not reach Example"):
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
    with pytest.raises(TriageError, match="Unexpected Example response"):
        evaluator.post({})


def test_close_closes_the_client():
    evaluator = HttpEvaluator(url=URL, api_key="k", label="Example")
    assert not evaluator.is_closed
    evaluator.close()
    assert evaluator.is_closed
