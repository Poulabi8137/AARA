from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_active_user,
    get_email_service,
    get_jwt_handler,
)
from app.auth.rbac import Role
from app.core.database import get_db
from app.repositories.password_reset_repository import PasswordResetTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.email_service import EmailService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

GENERIC_RESET_REQUESTED_MESSAGE = (
    "If an account exists with that email, a password reset link has been sent."
)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    jwt_handler=Depends(get_jwt_handler),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository()
    hashed = await jwt_handler.hash_password(body.password)
    try:
        user = await repo.create(
            db,
            email=body.email,
            display_name=body.display_name,
            hashed_password=hashed,
            role=Role.RESEARCHER,
            is_active=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        ) from exc

    # Registration logs the user in immediately, matching the frontend's
    # expectation of landing on the dashboard right after sign-up.
    access_token = await jwt_handler.create_access_token(subject=user.id)
    refresh_token = await jwt_handler.create_refresh_token(subject=user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    jwt_handler=Depends(get_jwt_handler),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository()
    user = await repo.get_by_email(db, body.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.hashed_password or not await jwt_handler.verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token = await jwt_handler.create_access_token(subject=user.id)
    refresh_token = await jwt_handler.create_refresh_token(subject=user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshTokenRequest,
    jwt_handler=Depends(get_jwt_handler),
):
    try:
        new_access = await jwt_handler.refresh_access_token(body.refresh_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc
    return TokenResponse(
        access_token=new_access,
        refresh_token=body.refresh_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: UserResponse = Depends(get_current_active_user),
):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: UserResponse = Depends(get_current_active_user),
) -> None:
    # Tokens are stateless JWTs; the client discards them on logout. This
    # endpoint exists so the frontend has a real call to make and a place to
    # hook in a revocation/blocklist later if needed.
    return None


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: PasswordResetRequest,
    request: Request,
    email_service: EmailService = Depends(get_email_service),
    db: AsyncSession = Depends(get_db),
):
    context = request.app.state.context
    config = context.config

    user_repo = UserRepository()
    token_repo = PasswordResetTokenRepository()

    user = await user_repo.get_by_email(db, body.email)
    if user and user.is_active:
        await token_repo.invalidate_active_tokens_for_user(db, user.id)

        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=config.password_reset_token_expire_minutes
        )
        await token_repo.create(
            db,
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
        )

        reset_link = f"{config.frontend_url.rstrip('/')}/reset-password?token={raw_token}"
        email_service.send_password_reset_email(user.email, reset_link)

    return MessageResponse(message=GENERIC_RESET_REQUESTED_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: PasswordResetConfirmRequest,
    jwt_handler=Depends(get_jwt_handler),
    db: AsyncSession = Depends(get_db),
):
    token_repo = PasswordResetTokenRepository()
    user_repo = UserRepository()

    token_hash = _hash_token(body.token)
    reset_token = await token_repo.get_by_token_hash(db, token_hash)

    if reset_token is None or reset_token.is_used or reset_token.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has expired",
        )

    new_hashed_password = await jwt_handler.hash_password(body.new_password)
    await user_repo.update(db, reset_token.user_id, hashed_password=new_hashed_password)
    await token_repo.mark_used(db, reset_token)

    return MessageResponse(message="Your password has been reset successfully")
