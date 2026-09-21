import logging

import httpx

from app.config import Settings
from app.triage.http import RetryPolicy
from app.triage.jev import JevTriageProvider
from app.triage.mock import MockTriageProvider
from app.triage.port import TriageProvider
from app.triage.typesafe import TypeSafeTriageProvider

log = logging.getLogger(__name__)


def build_provider(settings: Settings) -> TriageProvider:
    """auto: typesafe with a TypeSafe key, else jev with a gateway key, else mock.

    typesafe / jev / mock force the choice; a forced provider without its key fails at boot.
    """
    choice = settings.triage_provider
    if choice == "auto":
        if settings.typesafe_api_key:
            choice = "typesafe"
        elif settings.ai_gateway_api_key:
            choice = "jev"
        else:
            log.warning("No TYPESAFE_API_KEY or AI_GATEWAY_API_KEY: running in mock triage mode")
            choice = "mock"
    if choice == "mock":
        return MockTriageProvider()
    if choice == "typesafe":
        if not settings.typesafe_api_key:
            raise ValueError("TRIAGE_PROVIDER=typesafe requires TYPESAFE_API_KEY")
        return TypeSafeTriageProvider(
            api_key=settings.typesafe_api_key,
            model_id=settings.typesafe_model_id,
            base_url=settings.typesafe_base_url,
            timeout=_timeout(settings),
            retry=_retry(settings),
        )
    if not settings.ai_gateway_api_key:
        raise ValueError("TRIAGE_PROVIDER=jev requires AI_GATEWAY_API_KEY")
    return JevTriageProvider(
        api_key=settings.ai_gateway_api_key,
        model_id=settings.jev_model_id,
        evaluate_url=settings.ai_gateway_evaluate_url,
        timeout=_timeout(settings),
        retry=_retry(settings),
    )


def _timeout(settings: Settings) -> httpx.Timeout:
    read = settings.triage_read_timeout_seconds
    return httpx.Timeout(
        connect=settings.triage_connect_timeout_seconds, read=read, write=read, pool=read
    )


def _retry(settings: Settings) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=settings.triage_max_attempts,
        deadline_seconds=settings.triage_deadline_seconds,
    )
