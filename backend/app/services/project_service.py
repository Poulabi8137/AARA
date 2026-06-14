from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.research_project import ResearchProject, ProjectStatus
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(
        self,
        user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ResearchProject], int]:
        query = select(ResearchProject).where(
            ResearchProject.created_by == user.id
        ).order_by(ResearchProject.created_at.desc()).offset(skip).limit(limit)

        count_query = select(func.count(ResearchProject.id)).where(
            ResearchProject.created_by == user.id
        )

        result = await self.db.execute(query)
        projects = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return projects, total

    async def get_project(self, project_id: uuid.UUID, user: User) -> ResearchProject:
        result = await self.db.execute(
            select(ResearchProject).where(
                ResearchProject.id == project_id,
                ResearchProject.created_by == user.id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    async def create_project(
        self, data: ProjectCreate, user: User
    ) -> ResearchProject:
        project = ResearchProject(
            title=data.title,
            description=data.description,
            created_by=user.id,
        )
        self.db.add(project)
        await self.db.flush()
        return project

    async def update_project(
        self, project_id: uuid.UUID, data: ProjectUpdate, user: User
    ) -> ResearchProject:
        project = await self.get_project(project_id, user)

        if data.title is not None:
            project.title = data.title
        if data.description is not None:
            project.description = data.description
        if data.status is not None:
            project.status = data.status

        await self.db.flush()
        return project

    async def delete_project(self, project_id: uuid.UUID, user: User) -> None:
        project = await self.get_project(project_id, user)
        await self.db.delete(project)
        await self.db.flush()
