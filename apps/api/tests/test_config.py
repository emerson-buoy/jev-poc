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


def test_auto_prefers_typesafe_key_over_gateway_key():
    both = settings(typesafe_api_key="t", ai_gateway_api_key="g")
    assert build_provider(both).name == "typesafe"
    assert build_provider(settings(typesafe_api_key="t")).name == "typesafe"


def test_forced_typesafe_without_key_fails():
    with pytest.raises(ValueError, match="TYPESAFE_API_KEY"):
        build_provider(settings(triage_provider="typesafe"))


def test_forced_jev_ignores_typesafe_key():
    forced = settings(typesafe_api_key="t", ai_gateway_api_key="g", triage_provider="jev")
    assert build_provider(forced).name == "jev"
