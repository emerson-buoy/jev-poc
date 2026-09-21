from fastapi.testclient import TestClient

from app import main
from app.triage.port import TicketContent, TriageEvaluation


class SpyProvider:
    name = "spy"

    def __init__(self) -> None:
        self.closed = False

    def evaluate(self, content: TicketContent) -> TriageEvaluation:
        raise NotImplementedError

    def close(self) -> None:
        self.closed = True


def test_shutdown_closes_the_provider(monkeypatch):
    spy = SpyProvider()
    monkeypatch.setattr(main, "build_provider", lambda settings: spy)
    app = main.create_app(seed=False)
    with TestClient(app):
        assert app.state.triage_provider is spy
        assert not spy.closed
    assert spy.closed
