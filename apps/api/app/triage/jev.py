"""Adapter over Vercel AI Gateway's evaluate endpoint for TypeSafe AI's Jev."""

from dataclasses import asdict

import httpx

from app.triage.port import (
    BooleanAnswer,
    ChoiceAnswer,
    ScoreAnswer,
    TicketContent,
    TriageError,
    TriageEvaluation,
)
from app.triage.questions import QUESTIONS

GATEWAY_EVALUATE_URL = "https://ai-gateway.vercel.sh/v1/evaluate"
REQUEST_TIMEOUT_SECONDS = 30.0


class JevTriageProvider:
    name = "jev"

    def __init__(
        self, api_key: str, model_id: str, evaluate_url: str = GATEWAY_EVALUATE_URL
    ) -> None:
        self._model_id = model_id
        self._url = evaluate_url
        # Auth is set once on the client, so every call inherits it.
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"}, timeout=REQUEST_TIMEOUT_SECONDS
        )

    def evaluate(self, content: TicketContent) -> TriageEvaluation:
        payload = {"model": self._model_id, "state": asdict(content), "questions": QUESTIONS}
        try:
            response = self._client.post(self._url, json=payload)
        except httpx.HTTPError as error:
            raise TriageError(f"Could not reach the AI Gateway: {error}") from error
        if response.is_error:
            raise TriageError(_error_message(response))
        return _parse(response.json())


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        detail = body.get("error", body)
        message = detail.get("message") if isinstance(detail, dict) else None
    except ValueError:
        message = None
    return f"AI Gateway returned {response.status_code}: {message or response.text[:200]}"


def _parse(body: dict) -> TriageEvaluation:
    try:
        answers = body["answers"]
        department = answers["department"]
        urgency = answers["urgency"]
        refund = answers["refund_requested"]
        return TriageEvaluation(
            department=ChoiceAnswer(
                choice=department["choice"], probabilities=department.get("probabilities")
            ),
            urgency=ScoreAnswer(
                score=float(urgency["score"]),
                probabilities=_int_keys(urgency.get("probabilities")),
            ),
            refund=BooleanAnswer(probability=float(refund["probability"])),
            confidence=_confidence(body.get("providerMetadata")),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise TriageError(f"Unexpected evaluate response: {error!r}") from error


def _int_keys(probabilities: dict | None) -> dict[int, float] | None:
    if probabilities is None:
        return None
    return {int(key): float(value) for key, value in probabilities.items()}


def _confidence(metadata: dict | None) -> dict[str, float] | None:
    typesafe = (metadata or {}).get("typesafe")
    confidence = typesafe.get("confidence") if isinstance(typesafe, dict) else None
    if not isinstance(confidence, dict):
        return None
    numeric = {k: float(v) for k, v in confidence.items() if isinstance(v, int | float)}
    return numeric or None
