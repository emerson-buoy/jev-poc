from fastapi import APIRouter

from app.schemas import MetaRead
from app.triage.service import TriageServiceDep

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=MetaRead)
def read_meta(triage: TriageServiceDep) -> MetaRead:
    return MetaRead(provider=triage.provider_name, mock=triage.provider_name == "mock")
