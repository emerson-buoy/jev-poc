import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute
from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine, init_db
from app.routers import meta, tickets
from app.seed import seed_tickets
from app.triage.circuit import CircuitBreaker
from app.triage.factory import build_provider

log = logging.getLogger(__name__)


def operation_id(route: APIRoute) -> str:
    """Stable operationIds (list_tickets, move_ticket) so the generated client reads well."""
    return route.name


def create_app(seed: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings = get_settings()
        app.state.triage_provider = build_provider(settings)
        app.state.circuit = CircuitBreaker(
            failure_threshold=settings.triage_circuit_failures,
            cooldown_seconds=settings.triage_circuit_cooldown_seconds,
        )
        log.info("Triage provider: %s", app.state.triage_provider.name)
        if seed:
            engine = get_engine()
            init_db(engine)
            with Session(engine) as session:
                added = seed_tickets(session)
            if added:
                log.info("Seeded %d sample tickets", added)
        yield
        app.state.triage_provider.close()

    app = FastAPI(
        title="Jev Triage API",
        version="0.1.0",
        description="Tickets on a Kanban board, triaged by TypeSafe AI's Jev.",
        lifespan=lifespan,
        generate_unique_id_function=operation_id,
    )
    app.include_router(meta.router)
    app.include_router(tickets.router)
    return app


app = create_app()
