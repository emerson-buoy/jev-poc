import asyncio

import pytest

from app.events import Broadcaster, Notification
from app.routers.events import stream_events
from app.triage.port import ProviderUnavailable, TicketContent


def bound_broadcaster(maxsize: int = 100) -> Broadcaster:
    broadcaster = Broadcaster(maxsize=maxsize)
    broadcaster.bind(asyncio.get_running_loop())
    return broadcaster


@pytest.mark.anyio
async def test_delivers_each_notification_to_every_subscriber():
    bound = bound_broadcaster()
    first, second = bound.subscribe(), bound.subscribe()
    note = bound.publish(7, "created")
    assert note == Notification("1", 7, "created")
    assert await asyncio.wait_for(first.get(), 1) == note
    assert await asyncio.wait_for(second.get(), 1) == note
    assert bound.publish(7, "moved").id == "2"


@pytest.mark.anyio
async def test_unsubscribed_queue_receives_nothing():
    bound = bound_broadcaster()
    queue = bound.subscribe()
    bound.unsubscribe(queue)
    bound.publish(1, "created")
    await asyncio.sleep(0)
    assert queue.empty()
    assert bound.subscriber_count == 0


@pytest.mark.anyio
async def test_full_queue_drops_that_subscriber_without_blocking():
    broadcaster = bound_broadcaster(maxsize=1)
    slow, healthy = broadcaster.subscribe(), broadcaster.subscribe()
    broadcaster.publish(1, "created")
    assert (await asyncio.wait_for(healthy.get(), 1)).action == "created"
    broadcaster.publish(1, "updated")
    assert (await asyncio.wait_for(healthy.get(), 1)).action == "updated"
    assert slow.qsize() == 1
    assert broadcaster.subscriber_count == 1


@pytest.mark.anyio
async def test_publish_from_another_thread_reaches_the_loop():
    bound = bound_broadcaster()
    queue = bound.subscribe()
    await asyncio.to_thread(bound.publish, 3, "deleted")
    note = await asyncio.wait_for(queue.get(), 1)
    assert (note.ticket_id, note.action) == (3, "deleted")


def test_publish_without_a_loop_or_subscribers_is_harmless():
    assert Broadcaster().publish(1, "created").id == "1"


class FakeRequest:
    def __init__(self, connected_polls: int) -> None:
        self.connected_polls = connected_polls

    async def is_disconnected(self) -> bool:
        self.connected_polls -= 1
        return self.connected_polls < 0


@pytest.mark.anyio
async def test_stream_sends_the_retry_hint_then_each_notification():
    broadcaster = bound_broadcaster()
    stream = stream_events(FakeRequest(connected_polls=1), broadcaster)
    first = await anext(stream)
    assert (first.retry, first.comment) == (3000, "connected")
    assert broadcaster.subscriber_count == 1
    broadcaster.publish(9, "moved")
    event = await asyncio.wait_for(anext(stream), 2)
    assert (event.event, event.id) == ("tickets.changed", "1")
    assert event.data == {"id": 9, "action": "moved"}
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert broadcaster.subscriber_count == 0


@pytest.mark.anyio
async def test_closing_the_stream_unsubscribes():
    broadcaster = bound_broadcaster()
    stream = stream_events(FakeRequest(connected_polls=100), broadcaster)
    await anext(stream)
    await stream.aclose()
    assert broadcaster.subscriber_count == 0


def test_events_route_is_an_event_stream(client):
    operation = client.get("/openapi.json").json()["paths"]["/events"]["get"]
    assert operation["operationId"] == "stream_events"
    assert "text/event-stream" in operation["responses"]["200"]["content"]


class RecordingBroadcaster(Broadcaster):
    def __init__(self) -> None:
        super().__init__()
        self.published: list[tuple[int, str]] = []

    def publish(self, ticket_id, action):
        self.published.append((ticket_id, action))
        return super().publish(ticket_id, action)


@pytest.fixture
def broadcaster() -> RecordingBroadcaster:
    return RecordingBroadcaster()


def test_every_write_publishes_after_commit(client, broadcaster):
    created = client.post("/tickets", json={"title": "A", "description": "b"}).json()
    ticket_id = created["id"]
    client.patch(f"/tickets/{ticket_id}", json={"title": "B"})
    client.post(f"/tickets/{ticket_id}/move", json={"status": "triaged"})
    client.post(f"/tickets/{ticket_id}/move", json={"status": "done"})
    client.post(f"/tickets/{ticket_id}/triage")
    client.delete(f"/tickets/{ticket_id}")
    assert broadcaster.published == [
        (ticket_id, "created"),
        (ticket_id, "updated"),
        (ticket_id, "triaged"),
        (ticket_id, "moved"),
        (ticket_id, "triaged"),
        (ticket_id, "deleted"),
    ]


class Unavailable:
    name = "mock"

    def evaluate(self, content: TicketContent):
        raise ProviderUnavailable("down")

    def close(self) -> None:
        return None


@pytest.mark.parametrize("provider", [Unavailable()])
def test_rejected_move_publishes_nothing(client, broadcaster):
    created = client.post("/tickets", json={"title": "A", "description": "b"}).json()
    move = client.post(f"/tickets/{created['id']}/move", json={"status": "triaged"})
    assert move.status_code == 503
    assert broadcaster.published == [(created["id"], "created")]
