from dataclasses import dataclass
from typing import Protocol


class TriageError(Exception):
    pass


class ProviderUnavailable(TriageError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ProviderRejected(TriageError):
    pass


class MalformedResponse(TriageError):
    pass


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

    def close(self) -> None: ...
