from fastapi import APIRouter, HTTPException

from backend.nearby.nearby_models import NearbyPlanRequest, NearbyPlanResponse
from backend.nearby.nearby_service import generate_nearby_plan


router = APIRouter(prefix="/nearby", tags=["Nearby Planner"])


@router.post("/generate", response_model=NearbyPlanResponse)
def generate_nearby_plan_api(data: NearbyPlanRequest):
    try:
        return generate_nearby_plan(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
