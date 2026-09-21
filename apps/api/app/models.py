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


class Ticket(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    status: TicketStatus = Field(default=TicketStatus.NEW, index=True)
    department_override: str | None = None
    triage: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
