from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.research_report import ResearchReport
from app.schemas.report import ReportCreate


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_reports(
        self, skip: int = 0, limit: int = 50
    ) -> tuple[list[ResearchReport], int]:
        query = (
            select(ResearchReport)
            .order_by(ResearchReport.generated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(ResearchReport.id))

        result = await self.db.execute(query)
        reports = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return reports, total

    async def create_report(self, data: ReportCreate) -> ResearchReport:
        report = ResearchReport(
            project_id=data.project_id,
            report_type=data.report_type,
            report_path=data.report_path,
        )
        self.db.add(report)
        await self.db.flush()
        return report
