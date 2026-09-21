"""Ten sample tickets spread across every column. Results outside New are static fixtures."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models import Ticket, TicketStatus

SEED_TIME = datetime(2026, 9, 21, 9, 0, tzinfo=UTC).isoformat()


def _result(
    department: str,
    probabilities: dict[str, float],
    level: int,
    urgency: dict[str, float],
    refund: float,
) -> dict:
    mean = sum(int(k) * p for k, p in urgency.items())
    return {
        "department": department,
        "department_probabilities": probabilities,
        "urgency_score": round(mean - 1, 2),
        "urgency_level": level,
        "urgency_mean": round(mean, 2),
        "urgency_probabilities": urgency,
        "refund_requested": refund >= 0.5,
        "refund_probability": refund,
        "confidence": {
            "department": max(probabilities.values()),
            "urgency": max(urgency.values()),
            "refund_requested": round(abs(refund - 0.5) * 2, 2),
        },
        "provider": "seed",
        "triaged_at": SEED_TIME,
    }


SEED_TICKETS: list[dict] = [
    {
        "title": "Checkout returning 500 errors",
        "description": "Our checkout page has been throwing a 500 error for the last 20 minutes. "
        "We're losing sales every minute this stays down. Please escalate immediately.",
        "status": TicketStatus.NEW,
    },
    {
        "title": "Charged twice for October",
        "description": "I was charged twice for my October invoice. I'd like a refund for the "
        "duplicate charge as soon as possible.",
        "status": TicketStatus.NEW,
    },
    {
        "title": "Change display name?",
        "description": "Hi, just wondering if there's a way to change the display name on my "
        "account? No rush, whenever you get a chance.",
        "status": TicketStatus.NEW,
    },
    {
        "title": "CSV export garbles non-English names",
        "description": "The CSV export feature has been generating files with garbled characters "
        "for non-English names since yesterday's update. Not blocking us yet but it's affecting "
        "a few customers.",
        "status": TicketStatus.TRIAGED,
        "triage": _result(
            "technical",
            {"billing": 0.03, "technical": 0.91, "general": 0.06},
            3,
            {"1": 0.04, "2": 0.18, "3": 0.52, "4": 0.21, "5": 0.05},
            0.03,
        ),
    },
    {
        "title": "Plan renewed at a higher price",
        "description": "I noticed my plan renewed at a higher price than I expected. Can someone "
        "explain the pricing change? I just want clarity, not necessarily a refund.",
        "status": TicketStatus.TRIAGED,
        "triage": _result(
            "billing",
            {"billing": 0.88, "technical": 0.02, "general": 0.10},
            2,
            {"1": 0.22, "2": 0.51, "3": 0.19, "4": 0.06, "5": 0.02},
            0.31,
        ),
    },
    {
        "title": "App crashed and lost my work again",
        "description": "This is the third time your app has crashed and lost my work. I want a "
        "full refund immediately and I want this fixed today.",
        "status": TicketStatus.TRIAGED,
        "triage": _result(
            "technical",
            {"billing": 0.27, "technical": 0.68, "general": 0.05},
            5,
            {"1": 0.01, "2": 0.03, "3": 0.10, "4": 0.30, "5": 0.56},
            0.97,
        ),
    },
    {
        "title": "Webhook deliveries delayed by hours",
        "description": "Order webhooks are arriving 2 to 3 hours late since this morning. Our "
        "fulfilment team is working from manual exports until this is fixed.",
        "status": TicketStatus.IN_PROGRESS,
        "triage": _result(
            "technical",
            {"billing": 0.02, "technical": 0.94, "general": 0.04},
            4,
            {"1": 0.01, "2": 0.04, "3": 0.20, "4": 0.55, "5": 0.20},
            0.02,
        ),
    },
    {
        "title": "Need a VAT invoice for last quarter",
        "description": "Our accountant needs invoices with our VAT number for July to September. "
        "Can you regenerate them or tell me where to add the number?",
        "status": TicketStatus.IN_PROGRESS,
        "triage": _result(
            "billing",
            {"billing": 0.90, "technical": 0.03, "general": 0.07},
            2,
            {"1": 0.30, "2": 0.48, "3": 0.17, "4": 0.04, "5": 0.01},
            0.04,
        ),
    },
    {
        "title": "Feature request: dark mode",
        "description": "Love the product. Any plans for a dark mode? Half my team works late and "
        "keeps asking. Not urgent at all.",
        "status": TicketStatus.DONE,
        "triage": _result(
            "general",
            {"billing": 0.02, "technical": 0.18, "general": 0.80},
            1,
            {"1": 0.78, "2": 0.16, "3": 0.04, "4": 0.01, "5": 0.01},
            0.01,
        ),
    },
    {
        "title": "Cancelled but still billed",
        "description": "I cancelled my subscription on the 3rd and was still billed on the 10th. "
        "Please refund that charge and confirm the account is closed.",
        "status": TicketStatus.DONE,
        "triage": _result(
            "billing",
            {"billing": 0.95, "technical": 0.01, "general": 0.04},
            3,
            {"1": 0.05, "2": 0.20, "3": 0.50, "4": 0.20, "5": 0.05},
            0.93,
        ),
    },
]


def seed_tickets(session: Session) -> int:
    """Insert the samples when the table is empty. Returns how many rows were added."""
    if session.exec(select(Ticket).limit(1)).first() is not None:
        return 0
    for data in SEED_TICKETS:
        session.add(Ticket(**data))
    session.commit()
    return len(SEED_TICKETS)
