"""Deterministic keyword heuristics standing in for Jev when no API key is configured."""

import re

from app.triage.port import (
    BooleanAnswer,
    ChoiceAnswer,
    ScoreAnswer,
    TicketContent,
    TriageEvaluation,
)
from app.triage.questions import DEPARTMENTS, URGENCY_LEVELS

BILLING_WORDS = (
    "refund",
    "charged",
    "charge",
    "invoice",
    "billing",
    "price",
    "pricing",
    "payment",
    "subscription",
    "renew",
    "plan",
    "receipt",
)
TECHNICAL_WORDS = (
    "error",
    "crash",
    "bug",
    "outage",
    "down",
    "500",
    "broken",
    "export",
    "fail",
    "slow",
    "login",
    "integration",
    "api",
    "sync",
    "timeout",
    "garbled",
)
GENERAL_WORDS = ("account", "name", "feedback", "question", "wondering", "how do", "feature")

CRITICAL_WORDS = ("outage", "down", "500 error", "crash", "losing sales")
PRESSING_WORDS = ("immediately", "urgent", "asap", "today", "blocking", "escalate")
MODERATE_WORDS = ("affecting", "customers", "since", "every time", "third time")
HARM_WORDS = (
    "wrongly",
    "debited",
    "charged twice",
    "double charge",
    "unauthorized",
    "still billed",
    "lost my work",
    "lost data",
    "data loss",
    "losing money",
)
RELAXED_WORDS = ("no rush", "whenever", "just wondering", "not blocking", "no hurry")

NOT_REFUND = re.compile(r"\b(not|no)( necessarily)? (a |the )?refund", re.IGNORECASE)


class MockTriageProvider:
    name = "mock"

    def evaluate(self, content: TicketContent) -> TriageEvaluation:
        text = f"{content.title} {content.description}".lower()
        department = self._department(text)
        urgency = self._urgency(text)
        refund = self._refund(text)
        confidence = {
            "department": round(max(department.probabilities.values()), 2),
            "urgency": round(max(urgency.probabilities.values()), 2),
            "refund_requested": round(abs(refund.probability - 0.5) * 2, 2),
        }
        return TriageEvaluation(department, urgency, refund, confidence)

    def _department(self, text: str) -> ChoiceAnswer:
        hits = {
            "billing": _count(text, BILLING_WORDS),
            "technical": _count(text, TECHNICAL_WORDS),
            "general": _count(text, GENERAL_WORDS),
        }
        weights = {d: 1 + 3 * hits[d] for d in DEPARTMENTS}
        if not any(hits.values()):
            weights["general"] += 2
        probabilities = _normalize(weights)
        choice = max(DEPARTMENTS, key=lambda d: (probabilities[d], -DEPARTMENTS.index(d)))
        return ChoiceAnswer(choice, probabilities)

    def _urgency(self, text: str) -> ScoreAnswer:
        level = 1
        if _count(text, MODERATE_WORDS):
            level = 3
        if _count(text, PRESSING_WORDS) or _count(text, HARM_WORDS):
            level = 4
        if _count(text, CRITICAL_WORDS):
            level = 5
        if _count(text, RELAXED_WORDS):
            level = 1
        index = level - 1
        weights = {i: 0.05 for i in range(len(URGENCY_LEVELS))}
        weights[index] = 0.6
        for neighbour in (index - 1, index + 1):
            if 0 <= neighbour < len(URGENCY_LEVELS):
                weights[neighbour] = 0.15
        probabilities = _normalize(weights)
        return ScoreAnswer(score=index, probabilities=probabilities)

    def _refund(self, text: str) -> BooleanAnswer:
        if "refund" not in text:
            return BooleanAnswer(0.05)
        if NOT_REFUND.search(text):
            return BooleanAnswer(0.25)
        return BooleanAnswer(0.92)


def _count(text: str, words: tuple[str, ...]) -> int:
    return sum(text.count(word) for word in words)


def _normalize[K](weights: dict[K, float]) -> dict[K, float]:
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}
