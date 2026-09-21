import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import create_app
from app.seed import seed_tickets
from app.triage.mock import MockTriageProvider
from app.triage.port import TriageProvider
from app.triage.service import get_provider


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def provider() -> TriageProvider:
    return MockTriageProvider()


@pytest.fixture
def client(engine, provider):
    app = create_app(seed=False)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_provider] = lambda: provider
    with Session(engine) as session:
        seed_tickets(session)
    with TestClient(app) as client:
        yield client
