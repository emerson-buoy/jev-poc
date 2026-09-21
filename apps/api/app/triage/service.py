from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel

from app.triage.port import ScoreAnswer, TicketContent, TriageProvider

# P(true) at or above this counts as an explicit refund request.
REFUND_THRESHOLD = 0.5


class TriageResult(BaseModel):
    department: str
    department_probabilities: dict[str, float]
    urgency_score: float
    urgency_level: int
    urgency_mean: float
    urgency_probabilities: dict[str, float]
    refund_requested: bool
    refund_probability: float
    confidence: dict[str, float] | None = None
    provider: str
    triaged_at: datetime


class TriageService:
    def __init__(self, provider: TriageProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def triage(self, content: TicketContent) -> TriageResult:
        evaluation = self._provider.evaluate(content)
        return TriageResult(
            department=evaluation.department.choice,
            department_probabilities=evaluation.department.probabilities or {},
            urgency_score=evaluation.urgency.score,
            urgency_level=_pick_level(evaluation.urgency),
            urgency_mean=evaluation.urgency.score + 1,
            urgency_probabilities={
                str(index + 1): p for index, p in (evaluation.urgency.probabilities or {}).items()
            },
            refund_requested=evaluation.refund.probability >= REFUND_THRESHOLD,
            refund_probability=evaluation.refund.probability,
            confidence=evaluation.confidence,
            provider=self._provider.name,
            triaged_at=datetime.now(UTC),
        )


def _pick_level(urgency: ScoreAnswer) -> int:
    if not urgency.probabilities:
        return round(urgency.score) + 1
    index = max(urgency.probabilities, key=lambda i: (urgency.probabilities[i], -i))
    return index + 1


def get_provider(request: Request) -> TriageProvider:
    return request.app.state.triage_provider


def get_triage_service(provider: Annotated[TriageProvider, Depends(get_provider)]) -> TriageService:
    return TriageService(provider)


TriageServiceDep = Annotated[TriageService, Depends(get_triage_service)]
