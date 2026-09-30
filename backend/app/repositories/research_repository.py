"""Repositories for research projects and research tasks."""

from typing import List, Optional
from backend.app.models.db_models import ResearchProjectModel, ResearchTaskModel
from backend.app.repositories.base import BaseRepository
from backend.app.db.connection import DatabaseClient


class ResearchProjectRepository(BaseRepository[ResearchProjectModel]):
    """Repository handling research_projects table operations."""

    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(
            model_class=ResearchProjectModel,
            table_name="research_projects",
            db_client=db_client,
        )

    def get_by_status(self, status: str) -> List[ResearchProjectModel]:
        """Fetch all research projects with a specific status."""
        return self.filter({"status": status})


class ResearchTaskRepository(BaseRepository[ResearchTaskModel]):
    """Repository handling research_tasks table operations."""

    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(
            model_class=ResearchTaskModel,
            table_name="research_tasks",
            db_client=db_client,
        )

    def get_tasks_for_project(self, project_id: str) -> List[ResearchTaskModel]:
        """Fetch all tasks assigned to a specific research project ordered by priority."""
        tasks = self.filter({"research_project_id": project_id})
        return sorted(tasks, key=lambda t: t.priority)
