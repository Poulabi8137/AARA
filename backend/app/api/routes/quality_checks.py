from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_active_user
from app.schemas.auth import UserResponse
from app.schemas.quality import QualityCapability, QualityCheckRequest, QualityCheckResponse
from app.services.quality_check_service import QualityCheckService

router = APIRouter(prefix="/api/v1/quality", tags=["Quality Checks"])


def get_quality_check_service() -> QualityCheckService:
    return QualityCheckService()


@router.post("/{capability}/check", response_model=QualityCheckResponse)
async def run_quality_check(
    capability: QualityCapability,
    body: QualityCheckRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    service: QualityCheckService = Depends(get_quality_check_service),
):
    return await service.run_check(capability, body.text)
