from fastapi import APIRouter, Depends

from app.core.security import require_api_key
from app.models.drift import evaluate_drift
from app.schemas.drift import DriftRequest, DriftResult

router = APIRouter(prefix="/drift", tags=["drift"])


@router.post("/evaluate", response_model=DriftResult)
async def evaluate(request: DriftRequest, _: str = Depends(require_api_key)) -> DriftResult:
    """
    Evaluate a user's recent behavioral entries against their own rolling
    baseline. Returns a status of insufficient-data / steady / gentle-dip /
    check-in, plus the underlying per-signal breakdown for debugging or
    future UI use.
    """
    return evaluate_drift(entries=request.entries, reference_date=request.reference_date)
