from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel

from app.triage.circuit import CircuitBreaker, CircuitState
from app.triage.port import (
    ProviderUnavailable,
    ScoreAnswer,
    TicketContent,
    TriageError,
    TriageProvider,
)

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
    def __init__(self, provider: TriageProvider, circuit: CircuitBreaker) -> None:
        self._provider = provider
        self._circuit = circuit

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def circuit_state(self) -> CircuitState:
        return self._circuit.state

    def triage(self, content: TicketContent) -> TriageResult:
        evaluation = self._evaluate(content)
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

    def _evaluate(self, content: TicketContent):
        self._circuit.before_call()
        try:
            evaluation = self._provider.evaluate(content)
        except ProviderUnavailable:
            self._circuit.record_unavailable()
            raise
        except TriageError:
            self._circuit.record_available()
            raise
        self._circuit.record_available()
        return evaluation


def _pick_level(urgency: ScoreAnswer) -> int:
    if not urgency.probabilities:
        return round(urgency.score) + 1
    index = max(urgency.probabilities, key=lambda i: (urgency.probabilities[i], -i))
    return index + 1


def get_provider(request: Request) -> TriageProvider:
    return request.app.state.triage_provider


def get_circuit(request: Request) -> CircuitBreaker:
    return request.app.state.circuit


def get_triage_service(
    provider: Annotated[TriageProvider, Depends(get_provider)],
    circuit: Annotated[CircuitBreaker, Depends(get_circuit)],
) -> TriageService:
    return TriageService(provider, circuit)


TriageServiceDep = Annotated[TriageService, Depends(get_triage_service)]
