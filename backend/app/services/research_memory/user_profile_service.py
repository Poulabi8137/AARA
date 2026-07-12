from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.research_memory import UserResearchProfile
from app.schemas.research_memory import (
    UserResearchProfileCreate,
    UserResearchProfileUpdate,
)

logger = get_logger("services.research_memory.user_profile")


class UserResearchProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user_id: uuid.UUID) -> UserResearchProfile:
        result = await self.db.execute(
            select(UserResearchProfile).where(UserResearchProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User research profile not found",
            )
        return profile

    async def create_profile(
        self, user_id: uuid.UUID, data: UserResearchProfileCreate
    ) -> UserResearchProfile:
        existing = await self.db.execute(
            select(UserResearchProfile).where(UserResearchProfile.user_id == user_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User research profile already exists",
            )

        profile = UserResearchProfile(
            user_id=user_id,
            expertise_areas=data.expertise_areas,
            research_interests=data.research_interests,
            preferred_methodologies=data.preferred_methodologies,
            domains=data.domains,
            skill_level=data.skill_level,
            preferences=data.preferences,
        )
        self.db.add(profile)
        await self.db.flush()
        logger.info("created research profile", extra={"user_id": str(user_id)})
        return profile

    async def update_profile(
        self, user_id: uuid.UUID, data: UserResearchProfileUpdate
    ) -> UserResearchProfile:
        profile = await self.get_profile(user_id)

        if data.expertise_areas is not None:
            profile.expertise_areas = data.expertise_areas
        if data.research_interests is not None:
            profile.research_interests = data.research_interests
        if data.preferred_methodologies is not None:
            profile.preferred_methodologies = data.preferred_methodologies
        if data.domains is not None:
            profile.domains = data.domains
        if data.skill_level is not None:
            profile.skill_level = data.skill_level
        if data.preferences is not None:
            profile.preferences = data.preferences

        await self.db.flush()
        logger.info("updated research profile", extra={"user_id": str(user_id)})
        return profile

    async def update_expertise(
        self, user_id: uuid.UUID, expertise_areas: list[str]
    ) -> UserResearchProfile:
        profile = await self.get_profile(user_id)
        profile.expertise_areas = expertise_areas
        await self.db.flush()
        return profile

    async def update_interests(
        self, user_id: uuid.UUID, research_interests: list[str]
    ) -> UserResearchProfile:
        profile = await self.get_profile(user_id)
        profile.research_interests = research_interests
        await self.db.flush()
        return profile

    async def update_preferences(
        self, user_id: uuid.UUID, preferences: dict
    ) -> UserResearchProfile:
        profile = await self.get_profile(user_id)
        profile.preferences = preferences
        await self.db.flush()
        return profile

    async def delete_profile(self, user_id: uuid.UUID) -> None:
        profile = await self.get_profile(user_id)
        await self.db.delete(profile)
        await self.db.flush()
        logger.info("deleted research profile", extra={"user_id": str(user_id)})
