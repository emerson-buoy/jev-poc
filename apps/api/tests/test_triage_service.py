from datetime import UTC, datetime

from app.triage.port import (
    BooleanAnswer,
    ChoiceAnswer,
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


def triage(ev: TriageEvaluation):
    provider = StubProvider(ev)
    service = TriageService(provider)
    return service.triage(TicketContent(title="t", description="d")), provider


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
