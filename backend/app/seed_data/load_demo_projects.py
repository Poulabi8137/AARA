"""Load demo projects into the database for showcase purposes.

Usage:
    python -m app.seed_data.load_demo_projects              # Load all projects
    python -m app.seed_data.load_demo_projects --dry-run    # Preview without inserting
    python -m app.seed_data.load_demo_projects --clear      # Clear existing demo data first
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate

logger = get_logger("seed_data.load_demo_projects")


async def load_demo_projects(
    dry_run: bool = False,
    clear_first: bool = False,
) -> None:
    """Load all demo projects into the database."""
    from app.seed_data.demo_projects import DEMO_PROJECTS

    repo = ProjectRepository()

    if clear_first:
        logger.info("Clearing existing demo data...")
        existing = await repo.list_projects()
        for p in existing:
            if "demo" in (p.description or "").lower() or "showcase" in (p.description or "").lower():
                await repo.delete_project(p.id)
                logger.info(f"  Deleted: {p.title}")

    if dry_run:
        logger.info(f"DRY RUN — Would insert {len(DEMO_PROJECTS)} demo projects:")
        for p in DEMO_PROJECTS:
            logger.info(f"  [{p['difficulty']}] {p['title']} (expected: {p['expected_quality_score']}/100)")
        return

    count = 0
    for project_data in DEMO_PROJECTS:
        project = ProjectCreate(
            title=project_data["title"],
            description=(
                f"{project_data['description']}\n\n"
                f"Category: {project_data['category']}\n"
                f"Difficulty: {project_data['difficulty']}\n"
                f"Expected Quality Score: {project_data['expected_quality_score']}/100\n"
                f"Tags: {', '.join(project_data['tags'])}"
            ),
        )
        try:
            created = await repo.create_project(project)
            logger.info(f"  ✓ Created: {created.title} ({created.id})")
            count += 1
        except Exception as e:
            logger.error(f"  ✗ Failed: {project_data['title']}: {e}")

    logger.info(f"\nSuccessfully loaded {count}/{len(DEMO_PROJECTS)} demo projects.")


def main():
    parser = argparse.ArgumentParser(description="Load demo projects into the database")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")
    parser.add_argument("--clear", action="store_true", help="Clear existing demo data first")
    args = parser.parse_args()

    asyncio.run(load_demo_projects(dry_run=args.dry_run, clear_first=args.clear_first))


if __name__ == "__main__":
    main()
