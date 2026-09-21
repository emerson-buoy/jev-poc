"""Provider-neutral triage contract. No HTTP or framework types cross this boundary."""

from dataclasses import dataclass
from typing import Protocol


class TriageError(Exception):
    """Raised by a provider when an evaluation cannot be produced."""


@dataclass(frozen=True)
class TicketContent:
    title: str
    description: str


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    probabilities: dict[str, float] | None = None


@dataclass(frozen=True)
class ScoreAnswer:
    """score is a fractional 0-based position over the ordered levels."""

    score: float
    probabilities: dict[int, float] | None = None


@dataclass(frozen=True)
class BooleanAnswer:
    probability: float


@dataclass(frozen=True)
class TriageEvaluation:
    department: ChoiceAnswer
    urgency: ScoreAnswer
    refund: BooleanAnswer
    confidence: dict[str, float] | None = None


class TriageProvider(Protocol):
    name: str

    def evaluate(self, content: TicketContent) -> TriageEvaluation: ...
