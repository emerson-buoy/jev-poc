import pytest

from app.config import Settings
from app.triage.factory import build_provider


def settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def test_auto_without_key_is_mock():
    assert build_provider(settings()).name == "mock"


def test_auto_with_key_is_jev():
    assert build_provider(settings(ai_gateway_api_key="k")).name == "jev"


def test_forced_mock_ignores_key():
    assert build_provider(settings(ai_gateway_api_key="k", triage_provider="mock")).name == "mock"


def test_forced_jev_without_key_fails():
    with pytest.raises(ValueError, match="AI_GATEWAY_API_KEY"):
        build_provider(settings(triage_provider="jev"))


def test_defaults():
    s = settings()
    assert s.jev_model_id == "typesafe-ai/jev"
    assert s.triage_provider == "auto"
    assert s.database_url.startswith("sqlite:///")
