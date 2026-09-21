"""The three typed questions asked of every ticket. Shared by every provider."""

DEPARTMENTS: tuple[str, ...] = ("billing", "technical", "general")

# Urgency weighs time pressure and harm together. Harm means money, data or trust:
# a wrong charge blocks nothing but still deserves a fast response.
URGENCY_LEVELS: tuple[str, ...] = (
    "No time pressure and no harm. Informational, cosmetic, or a question.",
    "Minor inconvenience with an easy workaround. No money or data at stake.",
    "Affecting some of the customer's work, or a small billing error or wrong charge. "
    "A workaround exists.",
    "Blocking part of the customer's work with no good workaround, or the customer is losing "
    "money, was charged for something they do not owe, or lost data.",
    "Active outage, the customer is blocked right now, or significant financial or data harm "
    "is ongoing.",
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
            "Rate how urgent this ticket is, weighing time pressure and harm to the customer "
            "together. Level 1 means no time pressure and no harm. Level 5 means an active "
            "outage, a customer blocked right now, or significant ongoing financial or data harm."
        ),
        "criteria": list(URGENCY_LEVELS),
    },
    "refund_requested": {
        "type": "boolean",
        "instructions": "Is the customer explicitly asking for a refund?",
    },
}
