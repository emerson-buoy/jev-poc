from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import DiscardReason, TicketStatus
from app.triage.questions import DEPARTMENTS
from app.triage.service import TriageResult

Department = Literal["billing", "technical", "general"]
assert set(Department.__args__) == set(DEPARTMENTS)  # noqa: S101


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)


class TicketUpdate(BaseModel):
    """PATCH body. Fields left out are untouched; department_override may be set to null."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    department_override: Department | None = None


class MoveRequest(BaseModel):
    status: TicketStatus


class TriageRecordRead(BaseModel):
    id: int
    result: TriageResult
    department_override: Department | None
    reason: DiscardReason
    discarded_at: datetime


class TicketRead(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus
    department_override: Department | None
    triage: TriageResult | None
    effective_department: Department | None
    history: list[TriageRecordRead]
    created_at: datetime
    updated_at: datetime


class MetaRead(BaseModel):
    provider: str
    mock: bool
