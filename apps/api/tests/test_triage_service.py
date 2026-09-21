from datetime import UTC, datetime

import pytest

from app.triage.circuit import CircuitBreaker
from app.triage.port import (
    BooleanAnswer,
    ChoiceAnswer,
    ProviderUnavailable,
    ScoreAnswer,
    TicketContent,
    TriageEvaluation,
)
from app.triage.service import REFUND_THRESHOLD, TriageService


class StubProvider:
    name = "stub"

    def __init__(self, evaluation: TriageEvaluation):
        self.evaluation = evaluation
        self.calls: list[TicketContent] = []

    def evaluate(self, content: TicketContent) -> TriageEvaluation:
        self.calls.append(content)
        return self.evaluation


def evaluation(**overrides) -> TriageEvaluation:
    base = dict(
        department=ChoiceAnswer(
            choice="billing", probabilities={"billing": 0.8, "technical": 0.15, "general": 0.05}
        ),
        urgency=ScoreAnswer(score=3.2, probabilities={0: 0.05, 1: 0.05, 2: 0.1, 3: 0.3, 4: 0.5}),
        refund=BooleanAnswer(probability=0.9),
        confidence=None,
    )
    base.update(overrides)
    return TriageEvaluation(**base)


CONTENT = TicketContent(title="t", description="d")


def triage(ev: TriageEvaluation):
    provider = StubProvider(ev)
    service = TriageService(provider, CircuitBreaker())
    return service.triage(CONTENT), provider


class UnavailableProvider:
    name = "down"

    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, content: TicketContent) -> TriageEvaluation:
        self.calls += 1
        raise ProviderUnavailable("down")


def test_unavailable_counts_against_the_circuit_and_reraises():
    circuit = CircuitBreaker(failure_threshold=2)
    service = TriageService(UnavailableProvider(), circuit)
    with pytest.raises(ProviderUnavailable):
        service.triage(CONTENT)
    assert circuit.state == "closed"
    with pytest.raises(ProviderUnavailable):
        service.triage(CONTENT)
    assert circuit.state == "open"


def test_open_circuit_skips_the_provider():
    circuit = CircuitBreaker(failure_threshold=1)
    provider = UnavailableProvider()
    service = TriageService(provider, circuit)
    with pytest.raises(ProviderUnavailable):
        service.triage(CONTENT)
    with pytest.raises(ProviderUnavailable):
        service.triage(CONTENT)
    assert provider.calls == 1
    assert service.circuit_state == "open"


def test_success_reports_a_closed_circuit():
    provider = StubProvider(evaluation())
    service = TriageService(provider, CircuitBreaker())
    service.triage(CONTENT)
    assert service.circuit_state == "closed"


def test_passes_content_to_provider():
    _, provider = triage(evaluation())
    assert provider.calls == [TicketContent(title="t", description="d")]


def test_maps_department_and_probabilities():
    result, _ = triage(evaluation())
    assert result.department == "billing"
    assert result.department_probabilities == {"billing": 0.8, "technical": 0.15, "general": 0.05}


def test_keeps_raw_score_and_derives_one_based_mean_and_level():
    result, _ = triage(evaluation())
    assert result.urgency_score == 3.2
    assert abs(result.urgency_mean - 4.2) < 1e-9
    assert result.urgency_level == 5
    assert result.urgency_probabilities == {"1": 0.05, "2": 0.05, "3": 0.1, "4": 0.3, "5": 0.5}


def test_rounds_score_for_level_without_distribution():
    result, _ = triage(evaluation(urgency=ScoreAnswer(score=1.6, probabilities=None)))
    assert result.urgency_level == 3
    assert result.urgency_probabilities == {}


def test_refund_threshold():
    at, _ = triage(evaluation(refund=BooleanAnswer(probability=REFUND_THRESHOLD)))
    below, _ = triage(evaluation(refund=BooleanAnswer(probability=REFUND_THRESHOLD - 0.01)))
    assert at.refund_requested is True
    assert below.refund_requested is False


def test_records_provider_name_and_time():
    result, _ = triage(evaluation(confidence={"department": 0.7}))
    assert result.provider == "stub"
    assert result.confidence == {"department": 0.7}
    assert result.triaged_at <= datetime.now(UTC)
