"""The three typed questions asked of every ticket. Shared by every provider."""

DEPARTMENTS: tuple[str, ...] = ("billing", "technical", "general")

URGENCY_LEVELS: tuple[str, ...] = (
    "No time pressure. Informational or cosmetic.",
    "Minor inconvenience with an easy workaround.",
    "Affecting some of the customer's work; workaround exists.",
    "Blocking part of the customer's work; no good workaround.",
    "Active outage or blocking issue affecting the customer right now.",
)

QUESTIONS: dict[str, dict] = {
    "department": {
        "type": "choice",
        "instructions": "Which team should handle this support ticket?",
        "criteria": {
            "billing": "Payments, invoicing, refunds, billing disputes",
            "technical": "Bugs, outages, errors, integration or product issues",
            "general": "Anything else - account questions, feedback, unclear requests",
        },
    },
    "urgency": {
        "type": "score",
        "instructions": (
            "Rate how urgent this ticket is. Level 1 means no time pressure, level 5 means "
            "an active outage or blocking issue affecting the customer right now."
        ),
        "criteria": list(URGENCY_LEVELS),
    },
    "refund_requested": {
        "type": "boolean",
        "instructions": "Is the customer explicitly asking for a refund?",
    },
}
