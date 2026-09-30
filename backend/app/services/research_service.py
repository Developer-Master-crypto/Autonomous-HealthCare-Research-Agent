"""Master research orchestration service coordinating research inquiry lifecycles."""

from typing import Dict, List, Optional

from backend.app.schemas.research import ResearchRequest, ResearchResponse, ResearchStatus
from backend.app.services.task_planner_service import TaskPlannerService
from backend.app.utils.logger import logger


class ResearchService:
    """Coordinates research sessions, task decomposition, and milestone aggregation."""

    def __init__(self, task_planner: Optional[TaskPlannerService] = None) -> None:
        self.task_planner = task_planner or TaskPlannerService()
        self._sessions: Dict[str, ResearchResponse] = {}

    def create_research(self, request: ResearchRequest) -> ResearchResponse:
        """Initialize a new research investigation session and decompose initial task plan."""
        session = ResearchResponse(
            query=request.query,
            region=request.region,
            status=ResearchStatus.CREATED,
        )

        # Decompose initial task sequence
        tasks = self.task_planner.plan_tasks(research_id=session.research_id, query=request.query)
        session.tasks = tasks
        session.status = ResearchStatus.PLANNING

        self._sessions[session.research_id] = session
        logger.info(
            f"Created research session [{session.research_id}] for region: '{session.region or 'General'}'. "
            f"Decomposed into {len(tasks)} tasks."
        )
        return session

    def get_research(self, research_id: str) -> Optional[ResearchResponse]:
        """Fetch an active or historical research session."""
        return self._sessions.get(research_id)

    def list_researches(self) -> List[ResearchResponse]:
        """List all research sessions."""
        return list(self._sessions.values())
