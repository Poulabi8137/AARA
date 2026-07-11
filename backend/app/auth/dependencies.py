from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import JWTHandler
from app.auth.rbac import Permission, RBACService
from app.core.database import get_db
from app.core.exceptions import AuthorizationError, NotFoundError
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserResponse
from app.services.email_service import EmailService

security = HTTPBearer(auto_error=False)
rbac_service = RBACService()


def get_jwt_handler(request: Request) -> JWTHandler:
    context = getattr(request.app.state, "context", None)
    if context is None:
        raise HTTPException(status_code=500, detail="Application not initialized")
    config = context.config
    return JWTHandler(
        secret=config.jwt_secret,
        algorithm=config.jwt_algorithm,
        access_token_ttl=config.jwt_expiration_minutes * 60,
        refresh_token_ttl=2592000,
    )


def get_email_service(request: Request) -> EmailService:
    context = getattr(request.app.state, "context", None)
    if context is None:
        raise HTTPException(status_code=500, detail="Application not initialized")
    config = context.config
    return EmailService(
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_username=config.smtp_username,
        smtp_password=config.smtp_password,
        smtp_from=config.smtp_from,
        smtp_use_tls=config.smtp_use_tls,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )
    try:
        payload = await jwt_handler.verify_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    repo = UserRepository()
    try:
        user = await repo.get(db, user_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ) from None
    return UserResponse.model_validate(user)


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


def require_permission(
    permission: Permission,
) -> Callable[[UserResponse], Coroutine[Any, Any, None]]:
    async def check(current_user: UserResponse = Depends(get_current_active_user)) -> None:
        try:
            rbac_service.check_permission(current_user.role, permission)
        except AuthorizationError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from None
    return check


def require_role(min_role: str) -> Callable[[UserResponse], Coroutine[Any, Any, None]]:
    role_hierarchy = {"student": 0, "researcher": 1, "admin": 2, "super_admin": 3}

    async def check(current_user: UserResponse = Depends(get_current_active_user)) -> None:
        user_level = role_hierarchy.get(current_user.role, -1)
        required_level = role_hierarchy.get(min_role, 99)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{min_role}' or higher",
            )
    return check


async def get_workspace_id(path: str | None = None) -> str | None:
    return path
