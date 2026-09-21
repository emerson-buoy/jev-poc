import pytest

from app.triage.port import TicketContent, TriageError


def test_meta_reports_mock_provider(client):
    body = client.get("/meta").json()
    assert body == {"provider": "mock", "mock": True}


def test_seeded_tickets_span_all_columns(client):
    tickets = client.get("/tickets").json()
    assert len(tickets) == 10
    statuses = {t["status"] for t in tickets}
    assert statuses == {"new", "triaged", "in_progress", "done"}
    for t in tickets:
        if t["status"] == "new":
            assert t["triage"] is None
        else:
            assert t["triage"]["provider"] == "seed"
            assert t["effective_department"] == t["triage"]["department"]


def test_create_ticket_lands_in_new(client):
    res = client.post("/tickets", json={"title": "Hi", "description": "Need help"})
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "new"
    assert body["triage"] is None
    assert body["effective_department"] is None
    assert client.get(f"/tickets/{body['id']}").json() == body


def test_create_requires_title_and_description(client):
    assert client.post("/tickets", json={"title": "", "description": "x"}).status_code == 422
    assert client.post("/tickets", json={"title": "x"}).status_code == 422


def test_move_to_triaged_runs_triage(client):
    created = client.post(
        "/tickets", json={"title": "Charged twice", "description": "Please refund the duplicate."}
    ).json()
    res = client.post(f"/tickets/{created['id']}/move", json={"status": "triaged"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "triaged"
    assert body["triage"]["provider"] == "mock"
    assert body["triage"]["department"] == "billing"
    assert body["triage"]["refund_requested"] is True
    assert 1 <= body["triage"]["urgency_level"] <= 5
    assert body["effective_department"] == "billing"


def test_move_to_triaged_keeps_existing_result(client, provider):
    created = client.post("/tickets", json={"title": "A", "description": "outage"}).json()
    first = client.post(f"/tickets/{created['id']}/move", json={"status": "triaged"}).json()
    back = client.post(f"/tickets/{created['id']}/move", json={"status": "new"}).json()
    assert back["status"] == "new"
    assert back["triage"] == first["triage"]
    again = client.post(f"/tickets/{created['id']}/move", json={"status": "triaged"}).json()
    assert again["triage"] == first["triage"]


def test_move_between_other_columns_does_not_triage(client):
    created = client.post("/tickets", json={"title": "A", "description": "b"}).json()
    done = client.post(f"/tickets/{created['id']}/move", json={"status": "done"}).json()
    assert done["status"] == "done"
    assert done["triage"] is None


def test_move_rejects_unknown_status(client):
    created = client.post("/tickets", json={"title": "A", "description": "b"}).json()
    assert client.post(f"/tickets/{created['id']}/move", json={"status": "nope"}).status_code == 422


class FailingProvider:
    name = "mock"

    def evaluate(self, content: TicketContent):
        raise TriageError("gateway exploded")


@pytest.mark.parametrize("provider", [FailingProvider()])
def test_triage_failure_rejects_move(client):
    created = client.post("/tickets", json={"title": "A", "description": "b"}).json()
    res = client.post(f"/tickets/{created['id']}/move", json={"status": "triaged"})
    assert res.status_code == 502
    assert "gateway exploded" in res.json()["detail"]
    assert client.get(f"/tickets/{created['id']}").json()["status"] == "new"


def test_retriage_replaces_result(client):
    seeded = next(t for t in client.get("/tickets").json() if t["status"] == "triaged")
    res = client.post(f"/tickets/{seeded['id']}/triage")
    assert res.status_code == 200
    assert res.json()["triage"]["provider"] == "mock"
    assert res.json()["status"] == "triaged"


def test_department_override(client):
    seeded = next(t for t in client.get("/tickets").json() if t["status"] == "triaged")
    other = "general" if seeded["triage"]["department"] != "general" else "billing"
    res = client.patch(f"/tickets/{seeded['id']}", json={"department_override": other})
    assert res.status_code == 200
    assert res.json()["department_override"] == other
    assert res.json()["effective_department"] == other
    assert res.json()["triage"]["department"] == seeded["triage"]["department"]
    cleared = client.patch(f"/tickets/{seeded['id']}", json={"department_override": None}).json()
    assert cleared["effective_department"] == seeded["triage"]["department"]


def test_override_must_be_a_known_department(client):
    seeded = client.get("/tickets").json()[0]
    res = client.patch(f"/tickets/{seeded['id']}", json={"department_override": "legal"})
    assert res.status_code == 422


def test_update_title_and_description(client):
    created = client.post("/tickets", json={"title": "A", "description": "b"}).json()
    res = client.patch(f"/tickets/{created['id']}", json={"title": "B", "description": "c"})
    assert res.json()["title"] == "B"
    assert res.json()["description"] == "c"


def test_delete_ticket(client):
    created = client.post("/tickets", json={"title": "A", "description": "b"}).json()
    assert client.delete(f"/tickets/{created['id']}").status_code == 204
    assert client.get(f"/tickets/{created['id']}").status_code == 404


def test_unknown_ticket_is_404(client):
    assert client.get("/tickets/9999").status_code == 404
    assert client.post("/tickets/9999/move", json={"status": "done"}).status_code == 404
