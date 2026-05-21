from fastapi import APIRouter

from backend.nearby.nearby_models import NearbyPlanRequest, NearbyPlanResponse
from backend.nearby.nearby_service import generate_nearby_plan


router = APIRouter(prefix="/nearby", tags=["Nearby Planner"])


@router.post("/generate", response_model=NearbyPlanResponse)
def generate_nearby_plan_api(data: NearbyPlanRequest):
    return generate_nearby_plan(data)
