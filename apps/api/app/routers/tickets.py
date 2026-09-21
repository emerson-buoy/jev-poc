import logging
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, select

from app.db import get_session
from app.models import DiscardReason, Ticket, TicketStatus, TriageRecord, utcnow
from app.schemas import MoveRequest, TicketCreate, TicketRead, TicketUpdate, TriageRecordRead
from app.triage.port import ProviderRejected, ProviderUnavailable, TicketContent, TriageError
from app.triage.service import TriageService, TriageServiceDep

log = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])

SessionDep = Annotated[Session, Depends(get_session)]


def load_history(session: Session, ticket_id: int) -> list[TriageRecordRead]:
    records = session.exec(
        select(TriageRecord)
        .where(TriageRecord.ticket_id == ticket_id)
        .order_by(col(TriageRecord.id).desc())
    ).all()
    return [TriageRecordRead.model_validate(r, from_attributes=True) for r in records]


def to_read(ticket: Ticket, history: list[TriageRecordRead]) -> TicketRead:
    suggested = ticket.triage["department"] if ticket.triage else None
    return TicketRead(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        department_override=ticket.department_override,
        triage=ticket.triage,
        effective_department=ticket.department_override or suggested,
        history=history,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def read(session: Session, ticket: Ticket) -> TicketRead:
    return to_read(ticket, load_history(session, ticket.id))


def discard_triage(session: Session, ticket: Ticket, reason: DiscardReason) -> None:
    """Archives the active result and override, then clears both. No-op without a result."""
    if ticket.triage is None:
        return
    session.add(
        TriageRecord(
            ticket_id=ticket.id,
            result=ticket.triage,
            department_override=ticket.department_override,
            reason=reason,
        )
    )
    ticket.triage = None
    ticket.department_override = None


def load_ticket(ticket_id: int, session: SessionDep) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No ticket with id {ticket_id}")
    return ticket


TicketDep = Annotated[Ticket, Depends(load_ticket)]


def run_triage(ticket: Ticket, triage: TriageService) -> None:
    content = TicketContent(title=ticket.title, description=ticket.description)
    try:
        ticket.triage = triage.triage(content).model_dump(mode="json")
    except TriageError as error:
        log.warning("Triage of ticket %s failed: %s", ticket.id, error)
        raise _http_error(error) from error


def _http_error(error: TriageError) -> HTTPException:
    if isinstance(error, ProviderUnavailable):
        headers = {"Retry-After": str(ceil(error.retry_after))} if error.retry_after else None
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Triage is temporarily unavailable, try again",
            headers=headers,
        )
    if isinstance(error, ProviderRejected):
        return HTTPException(status.HTTP_502_BAD_GATEWAY, "Triage provider rejected the request")
    return HTTPException(
        status.HTTP_502_BAD_GATEWAY, "Triage provider returned an unusable response"
    )


def save(session: Session, ticket: Ticket) -> TicketRead:
    ticket.updated_at = utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return read(session, ticket)


@router.get("", response_model=list[TicketRead])
def list_tickets(session: SessionDep) -> list[TicketRead]:
    tickets = session.exec(select(Ticket).order_by(Ticket.created_at, Ticket.id)).all()
    return [read(session, t) for t in tickets]


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(body: TicketCreate, session: SessionDep) -> TicketRead:
    return save(session, Ticket(title=body.title, description=body.description))


@router.get("/{ticket_id}", response_model=TicketRead)
def read_ticket(ticket: TicketDep, session: SessionDep) -> TicketRead:
    return read(session, ticket)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket: TicketDep, body: TicketUpdate, session: SessionDep) -> TicketRead:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    return save(session, ticket)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket: TicketDep, session: SessionDep) -> None:
    for record in session.exec(select(TriageRecord).where(TriageRecord.ticket_id == ticket.id)):
        session.delete(record)
    session.delete(ticket)
    session.commit()


@router.post("/{ticket_id}/move", response_model=TicketRead)
def move_ticket(
    ticket: TicketDep, body: MoveRequest, session: SessionDep, triage: TriageServiceDep
) -> TicketRead:
    """Into Triaged runs triage once. Into New discards the result to history. Else free."""
    if body.status == TicketStatus.TRIAGED and ticket.triage is None:
        run_triage(ticket, triage)
    if body.status == TicketStatus.NEW:
        discard_triage(session, ticket, DiscardReason.MOVED_TO_NEW)
    ticket.status = body.status
    return save(session, ticket)


@router.post("/{ticket_id}/triage", response_model=TicketRead)
def retriage_ticket(ticket: TicketDep, session: SessionDep, triage: TriageServiceDep) -> TicketRead:
    discard_triage(session, ticket, DiscardReason.RETRIAGED)
    run_triage(ticket, triage)
    if ticket.status == TicketStatus.NEW:
        ticket.status = TicketStatus.TRIAGED
    return save(session, ticket)
