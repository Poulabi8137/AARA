from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    _, access_token, refresh_token = await service.register(
        name=body.name,
        email=body.email,
        password=body.password,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    _, access_token, refresh_token = await service.login(
        email=body.email,
        password=body.password,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    access_token, refresh_token = await service.refresh(
        refresh_token=body.refresh_token,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat(),
    )
