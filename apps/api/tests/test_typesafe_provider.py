import httpx
import pytest
import respx

from app.triage.port import TicketContent, TriageError
from app.triage.typesafe import TypeSafeTriageProvider

BASE_URL = "https://api.typesafe.ai/v1"
URL = f"{BASE_URL}/systemone"

TYPESAFE_RESPONSE = {
    "model": "jev-latest",
    "answers": {
        "department": {
            "type": "choice",
            "choice": "billing",
            "probabilities": {"billing": 0.88, "technical": 0.08, "general": 0.04},
            "confidence": 0.81,
        },
        "urgency": {
            "type": "score",
            "score": 1.05,
            "legend": {"0": "a", "1": "b", "2": "c", "3": "d", "4": "e"},
            "probabilities": {"0": 0.05, "1": 0.85, "2": 0.1, "3": 0.0, "4": 0.0},
            "confidence": 0.92,
        },
        "refund_requested": {"type": "noul", "noul": 0.95},
    },
    "usage": {"input_tokens": 120, "output_tokens": 12},
}

provider = TypeSafeTriageProvider(api_key="k", model_id="jev-latest", base_url=BASE_URL)
content = TicketContent(title="Charged twice", description="Please refund the duplicate.")


@respx.mock
def test_posts_typesafe_wire_format():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=TYPESAFE_RESPONSE))
    provider.evaluate(content)
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer k"
    body = httpx.Response(200, content=request.content).json()
    assert body["model"] == "jev-latest"
    assert body["state"] == {
        "title": "Charged twice",
        "description": "Please refund the duplicate.",
    }
    assert body["questions"]["department"]["type"] == "choice"
    assert body["questions"]["urgency"]["type"] == "score"
    assert len(body["questions"]["urgency"]["criteria"]) == 5
    assert body["questions"]["refund_requested"]["type"] == "noul"
    assert "boolean" not in {q["type"] for q in body["questions"].values()}


@respx.mock
def test_maps_answers_and_per_answer_confidence():
    respx.post(URL).mock(return_value=httpx.Response(200, json=TYPESAFE_RESPONSE))
    result = provider.evaluate(content)
    assert result.department.choice == "billing"
    assert result.department.probabilities == {"billing": 0.88, "technical": 0.08, "general": 0.04}
    assert result.urgency.score == 1.05
    assert result.urgency.probabilities == {0: 0.05, 1: 0.85, 2: 0.1, 3: 0.0, 4: 0.0}
    assert result.refund.probability == 0.95
    assert result.confidence == {"department": 0.81, "urgency": 0.92}


@respx.mock
def test_http_error_becomes_triage_error():
    respx.post(URL).mock(return_value=httpx.Response(401, json={"message": "Invalid API key"}))
    with pytest.raises(TriageError, match="401"):
        provider.evaluate(content)


@respx.mock
def test_network_error_becomes_triage_error():
    respx.post(URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(TriageError):
        provider.evaluate(content)


def test_provider_name():
    assert provider.name == "typesafe"
