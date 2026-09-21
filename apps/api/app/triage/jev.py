from dataclasses import asdict

import httpx

from app.triage.http import DEFAULT_TIMEOUT, HttpEvaluator, RetryPolicy
from app.triage.port import (
    BooleanAnswer,
    ChoiceAnswer,
    MalformedResponse,
    ScoreAnswer,
    TicketContent,
    TriageEvaluation,
)
from app.triage.questions import QUESTIONS

GATEWAY_EVALUATE_URL = "https://ai-gateway.vercel.sh/v1/evaluate"


class JevTriageProvider:
    name = "jev"

    def __init__(
        self,
        api_key: str,
        model_id: str,
        evaluate_url: str = GATEWAY_EVALUATE_URL,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        retry: RetryPolicy | None = None,
    ) -> None:
        self._model_id = model_id
        self._http = HttpEvaluator(
            url=evaluate_url, api_key=api_key, label="AI Gateway", timeout=timeout, retry=retry
        )

    def evaluate(self, content: TicketContent) -> TriageEvaluation:
        payload = {"model": self._model_id, "state": asdict(content), "questions": QUESTIONS}
        return _parse(self._http.post(payload))

    def close(self) -> None:
        self._http.close()


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
        raise MalformedResponse(f"Unexpected evaluate response: {error!r}") from error


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
