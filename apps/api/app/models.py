from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class TicketStatus(StrEnum):
    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in_progress"
    DONE = "done"


def utcnow() -> datetime:
    return datetime.now(UTC)


class DiscardReason(StrEnum):
    MOVED_TO_NEW = "moved_to_new"
    RETRIAGED = "retriaged"


class Ticket(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    status: TicketStatus = Field(default=TicketStatus.NEW, index=True)
    department_override: str | None = None
    triage: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class TriageRecord(SQLModel, table=True):
    """A triage result that is no longer active. Kept for history, never consulted."""

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    result: dict = Field(sa_column=Column(JSON))
    department_override: str | None = None
    reason: DiscardReason
    discarded_at: datetime = Field(default_factory=utcnow)
