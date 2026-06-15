"""Seed the database with realistic demo data for product showcasing.

Usage:
    python scripts/seed_demo.py

Requires:
    - PostgreSQL running with schema created
    - DATABASE_URL or .env configured
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.research_project import ResearchProject
from app.models.research_report import ResearchReport
from app.models.research_session import ResearchSession
from app.models.agent_execution import AgentExecution, ExecutionStatus
from app.schemas.report_generator import ResearchReport as ReportSchema

logger = get_logger("seed_demo")

DEMO_USER = {
    "name": "Alex Researcher",
    "email": "demo@aara.dev",
    "password": "Demo1234!",
}

DEMO_PROJECTS = [
    {
        "title": "Transformers in Drug Discovery",
        "description": "Investigating the application of transformer architectures for molecular property prediction and drug-target interaction modeling.",
    },
    {
        "title": "Quantum Error Correction",
        "description": "Survey of surface codes, topological codes, and fault-tolerant quantum computation approaches.",
    },
    {
        "title": "Climate-Conscious AI",
        "description": "Analyzing the carbon footprint of large-scale AI training and inference, and exploring green AI methodologies.",
    },
]

DEMO_AGENTS = ["planner", "retriever", "summarizer", "gap_detector", "report_generator"]


async def seed():
    logger.info("Starting demo data seeding...")

    async for db in get_db():
        try:
            # Create demo user
            existing = await db.execute(
                __import__("sqlalchemy").select(User).where(User.email == DEMO_USER["email"])
            )
            user = existing.scalar_one_or_none()

            if user:
                logger.info("Demo user already exists, skipping creation")
            else:
                user = User(
                    name=DEMO_USER["name"],
                    email=DEMO_USER["email"],
                    password_hash=hash_password(DEMO_USER["password"]),
                    role=UserRole.RESEARCHER,
                )
                db.add(user)
                await db.flush()
                logger.info(f"Created demo user: {user.email}")

            # Create projects with sessions
            for proj_data in DEMO_PROJECTS:
                existing_proj = await db.execute(
                    __import__("sqlalchemy").select(ResearchProject).where(
                        ResearchProject.title == proj_data["title"],
                        ResearchProject.created_by == user.id,
                    )
                )
                project = existing_proj.scalar_one_or_none()

                if project:
                    logger.info(f"Project '{proj_data['title']}' already exists, skipping")
                    continue

                project = ResearchProject(
                    title=proj_data["title"],
                    description=proj_data["description"],
                    created_by=user.id,
                )
                db.add(project)
                await db.flush()

                # Create a session
                session = ResearchSession(
                    project_id=project.id,
                    user_id=user.id,
                    status="completed",
                    state={
                        "query": proj_data["title"],
                        "objective": proj_data["description"],
                        "status": "report_generation_complete",
                        "errors": [],
                    },
                )
                db.add(session)
                await db.flush()

                # Create completed agent executions
                for i, agent_name in enumerate(DEMO_AGENTS):
                    execution = AgentExecution(
                        session_id=session.id,
                        agent_name=agent_name,
                        status=ExecutionStatus.COMPLETED,
                        input={"query": proj_data["title"]},
                        output={"status": "completed"},
                        duration_ms=(i + 1) * 2500,
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(execution)

                await db.flush()
                logger.info(f"Created project: '{proj_data['title']}' with demo data")

            await db.commit()
            logger.info("=" * 50)
            logger.info("Demo data seeded successfully!")
            logger.info(f"  User:     {DEMO_USER['email']} / {DEMO_USER['password']}")
            logger.info(f"  Projects: {len(DEMO_PROJECTS)}")
            logger.info(f"  Agents:   {len(DEMO_AGENTS)} per project")
            logger.info("=" * 50)

        except Exception as exc:
            await db.rollback()
            logger.error(f"Seeding failed: {exc}")
            raise


if __name__ == "__main__":
    asyncio.run(seed())
