import logging

from app.config import Settings
from app.triage.jev import JevTriageProvider
from app.triage.mock import MockTriageProvider
from app.triage.port import TriageProvider

log = logging.getLogger(__name__)


def build_provider(settings: Settings) -> TriageProvider:
    """auto: jev when a key is present, mock otherwise. jev/mock force the choice."""
    wants_jev = settings.triage_provider == "jev" or (
        settings.triage_provider == "auto" and bool(settings.ai_gateway_api_key)
    )
    if not wants_jev:
        if settings.triage_provider == "auto":
            log.warning("AI_GATEWAY_API_KEY not set: running in mock triage mode")
        return MockTriageProvider()
    if not settings.ai_gateway_api_key:
        raise ValueError("TRIAGE_PROVIDER=jev requires AI_GATEWAY_API_KEY")
    return JevTriageProvider(
        api_key=settings.ai_gateway_api_key,
        model_id=settings.jev_model_id,
        evaluate_url=settings.ai_gateway_evaluate_url,
    )
