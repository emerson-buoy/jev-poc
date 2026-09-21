from dataclasses import asdict

from app.triage.http import HttpEvaluator
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
YES_NO_TYPE = "noul"

_WIRE_QUESTIONS = {
    key: {**q, "type": YES_NO_TYPE} if q["type"] == "boolean" else q for key, q in QUESTIONS.items()
}


class TypeSafeTriageProvider:
    name = "typesafe"

    def __init__(
        self, api_key: str, model_id: str = DEFAULT_MODEL_ID, base_url: str = DEFAULT_BASE_URL
    ) -> None:
        self._model_id = model_id
        self._http = HttpEvaluator(
            url=f"{base_url.rstrip('/')}/systemone", api_key=api_key, label="TypeSafe"
        )

    def evaluate(self, content: TicketContent) -> TriageEvaluation:
        payload = {"model": self._model_id, "state": asdict(content), "questions": _WIRE_QUESTIONS}
        return _parse(self._http.post(payload))

    def close(self) -> None:
        self._http.close()


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
            refund=BooleanAnswer(probability=float(refund[YES_NO_TYPE])),
            confidence=confidence or None,
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise TriageError(f"Unexpected TypeSafe response: {error!r}") from error
