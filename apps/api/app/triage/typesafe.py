"""Adapter over TypeSafe AI's own System One endpoint. Same Jev, no gateway in between."""

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

DEFAULT_BASE_URL = "https://api.typesafe.ai/v1"
DEFAULT_MODEL_ID = "jev-latest"
REQUEST_TIMEOUT_SECONDS = 30.0

# TypeSafe's wire format calls the yes/no question type "noul".
_WIRE_QUESTIONS = {
    key: {**q, "type": "noul"} if q["type"] == "boolean" else q for key, q in QUESTIONS.items()
}


class TypeSafeTriageProvider:
    name = "typesafe"

    def __init__(
        self,
        api_key: str,
        model_id: str = DEFAULT_MODEL_ID,
        base_url: str = DEFAULT_BASE_URL,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._url = f"{base_url.rstrip('/')}/systemone"
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)

    def evaluate(self, content: TicketContent) -> TriageEvaluation:
        payload = {"model": self._model_id, "state": asdict(content), "questions": _WIRE_QUESTIONS}
        try:
            response = self._client.post(
                self._url, json=payload, headers={"Authorization": f"Bearer {self._api_key}"}
            )
        except httpx.HTTPError as error:
            raise TriageError(f"Could not reach TypeSafe: {error}") from error
        if response.is_error:
            raise TriageError(_error_message(response))
        return _parse(response.json())


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        message = body.get("message") or body.get("detail") if isinstance(body, dict) else None
    except ValueError:
        message = None
    return f"TypeSafe returned {response.status_code}: {message or response.text[:200]}"


def _parse(body: dict) -> TriageEvaluation:
    try:
        answers = body["answers"]
        department = answers["department"]
        urgency = answers["urgency"]
        refund = answers["refund_requested"]
        confidence = {
            key: float(answers[key]["confidence"])
            for key in ("department", "urgency", "refund_requested")
            if isinstance(answers[key].get("confidence"), int | float)
        }
        return TriageEvaluation(
            department=ChoiceAnswer(
                choice=department["choice"], probabilities=department.get("probabilities")
            ),
            urgency=ScoreAnswer(
                score=float(urgency["score"]),
                probabilities={int(k): float(v) for k, v in urgency["probabilities"].items()},
            ),
            refund=BooleanAnswer(probability=float(refund["noul"])),
            confidence=confidence or None,
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise TriageError(f"Unexpected TypeSafe response: {error!r}") from error
