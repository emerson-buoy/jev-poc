import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.events import BroadcasterDep

router = APIRouter(tags=["events"])

RECONNECT_MS = 3000
POLL_SECONDS = 1.0


@router.get("/events", response_class=EventSourceResponse)
async def stream_events(
    request: Request, broadcaster: BroadcasterDep
) -> AsyncIterator[ServerSentEvent]:
    queue = broadcaster.subscribe()
    try:
        yield ServerSentEvent(retry=RECONNECT_MS, comment="connected")
        while not await request.is_disconnected():
            try:
                note = await asyncio.wait_for(queue.get(), timeout=POLL_SECONDS)
            except TimeoutError:
                continue
            yield ServerSentEvent(
                event="tickets.changed",
                id=note.id,
                data={"id": note.ticket_id, "action": note.action},
            )
    finally:
        broadcaster.unsubscribe(queue)
