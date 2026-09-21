import httpx
import pytest
import respx

from app.triage.jev import GATEWAY_EVALUATE_URL, JevTriageProvider
from app.triage.port import TicketContent, TriageError

GATEWAY_RESPONSE = {
    "model": "typesafe-ai/jev",
    "answers": {
        "department": {
            "type": "choice",
            "choice": "billing",
            "probabilities": {"billing": 0.9, "technical": 0.05, "general": 0.05},
        },
        "urgency": {
            "type": "score",
            "score": 2.5,
            "probabilities": {"0": 0, "1": 0, "2": 0.5, "3": 0.5, "4": 0},
        },
        "refund_requested": {"type": "boolean", "probability": 0.95},
    },
    "providerMetadata": {"typesafe": {"confidence": {"department": 0.8, "urgency": 0.6}}},
}

provider = JevTriageProvider(api_key="k", model_id="typesafe-ai/jev")
content = TicketContent(title="Charged twice", description="Please refund the duplicate.")


@respx.mock
def test_posts_model_state_and_three_questions():
    route = respx.post(GATEWAY_EVALUATE_URL).mock(
        return_value=httpx.Response(200, json=GATEWAY_RESPONSE)
    )
    provider.evaluate(content)
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer k"
    body = httpx.Response(200, content=request.content).json()
    assert body["model"] == "typesafe-ai/jev"
    assert body["state"] == {
        "title": "Charged twice",
        "description": "Please refund the duplicate.",
    }
    assert body["questions"]["department"]["type"] == "choice"
    assert list(body["questions"]["department"]["criteria"]) == ["billing", "technical", "general"]
    assert body["questions"]["urgency"]["type"] == "score"
    assert len(body["questions"]["urgency"]["criteria"]) == 5
    assert body["questions"]["refund_requested"]["type"] == "boolean"


@respx.mock
def test_maps_answers_and_confidence():
    respx.post(GATEWAY_EVALUATE_URL).mock(return_value=httpx.Response(200, json=GATEWAY_RESPONSE))
    result = provider.evaluate(content)
    assert result.department.choice == "billing"
    assert result.department.probabilities == {"billing": 0.9, "technical": 0.05, "general": 0.05}
    assert result.urgency.score == 2.5
    assert result.urgency.probabilities == {0: 0, 1: 0, 2: 0.5, 3: 0.5, 4: 0}
    assert result.refund.probability == 0.95
    assert result.confidence == {"department": 0.8, "urgency": 0.6}


@respx.mock
def test_missing_confidence_is_none():
    body = {**GATEWAY_RESPONSE, "providerMetadata": {}}
    respx.post(GATEWAY_EVALUATE_URL).mock(return_value=httpx.Response(200, json=body))
    assert provider.evaluate(content).confidence is None


@respx.mock
def test_http_error_becomes_triage_error():
    respx.post(GATEWAY_EVALUATE_URL).mock(
        return_value=httpx.Response(401, json={"error": {"message": "Invalid API key"}})
    )
    with pytest.raises(TriageError, match="Invalid API key"):
        provider.evaluate(content)


@respx.mock
def test_network_error_becomes_triage_error():
    respx.post(GATEWAY_EVALUATE_URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(TriageError):
        provider.evaluate(content)


def test_provider_name():
    assert provider.name == "jev"
