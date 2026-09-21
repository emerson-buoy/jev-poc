import asyncio
from dataclasses import dataclass
from threading import Lock
from typing import Annotated, Literal

from fastapi import Depends, Request

TicketAction = Literal["created", "updated", "moved", "triaged", "deleted"]


@dataclass(frozen=True)
class Notification:
    id: str
    ticket_id: int
    action: TicketAction


class Broadcaster:
    def __init__(self, maxsize: int = 100) -> None:
        self._maxsize = maxsize
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = Lock()
        self._queues: set[asyncio.Queue[Notification]] = set()
        self._sequence = 0

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._queues)

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[Notification]:
        queue: asyncio.Queue[Notification] = asyncio.Queue(maxsize=self._maxsize)
        with self._lock:
            self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Notification]) -> None:
        with self._lock:
            self._queues.discard(queue)

    def publish(self, ticket_id: int, action: TicketAction) -> Notification:
        with self._lock:
            self._sequence += 1
            note = Notification(str(self._sequence), ticket_id, action)
            queues = list(self._queues)
        for queue in queues:
            if self._loop is None or self._loop.is_closed():
                self._deliver(queue, note)
            else:
                self._loop.call_soon_threadsafe(self._deliver, queue, note)
        return note

    def _deliver(self, queue: asyncio.Queue[Notification], note: Notification) -> None:
        try:
            queue.put_nowait(note)
        except asyncio.QueueFull:
            self.unsubscribe(queue)


def get_broadcaster(request: Request) -> Broadcaster:
    return request.app.state.broadcaster


BroadcasterDep = Annotated[Broadcaster, Depends(get_broadcaster)]
