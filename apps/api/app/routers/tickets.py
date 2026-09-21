from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import Ticket, TicketStatus, utcnow
from app.schemas import MoveRequest, TicketCreate, TicketRead, TicketUpdate
from app.triage.port import TicketContent, TriageError
from app.triage.service import TriageService, TriageServiceDep

router = APIRouter(prefix="/tickets", tags=["tickets"])

SessionDep = Annotated[Session, Depends(get_session)]


def to_read(ticket: Ticket) -> TicketRead:
    suggested = ticket.triage["department"] if ticket.triage else None
    return TicketRead(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        department_override=ticket.department_override,
        triage=ticket.triage,
        effective_department=ticket.department_override or suggested,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


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
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Triage failed: {error}") from error


def save(session: Session, ticket: Ticket) -> TicketRead:
    ticket.updated_at = utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return to_read(ticket)


@router.get("", response_model=list[TicketRead])
def list_tickets(session: SessionDep) -> list[TicketRead]:
    tickets = session.exec(select(Ticket).order_by(Ticket.created_at, Ticket.id)).all()
    return [to_read(t) for t in tickets]


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(body: TicketCreate, session: SessionDep) -> TicketRead:
    return save(session, Ticket(title=body.title, description=body.description))


@router.get("/{ticket_id}", response_model=TicketRead)
def read_ticket(ticket: TicketDep) -> TicketRead:
    return to_read(ticket)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket: TicketDep, body: TicketUpdate, session: SessionDep) -> TicketRead:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    return save(session, ticket)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket: TicketDep, session: SessionDep) -> None:
    session.delete(ticket)
    session.commit()


@router.post("/{ticket_id}/move", response_model=TicketRead)
def move_ticket(
    ticket: TicketDep, body: MoveRequest, session: SessionDep, triage: TriageServiceDep
) -> TicketRead:
    """Moving into Triaged runs triage once. Any other move is free. Failure leaves the ticket."""
    if body.status == TicketStatus.TRIAGED and ticket.triage is None:
        run_triage(ticket, triage)
    ticket.status = body.status
    return save(session, ticket)


@router.post("/{ticket_id}/triage", response_model=TicketRead)
def retriage_ticket(ticket: TicketDep, session: SessionDep, triage: TriageServiceDep) -> TicketRead:
    """Always asks the provider again and replaces the stored result."""
    run_triage(ticket, triage)
    return save(session, ticket)
