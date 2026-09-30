"""Task planner service for decomposing healthcare research queries into discrete sub-tasks."""

from typing import List
from backend.app.schemas.research import ResearchTask, TaskStatus
from backend.app.utils.logger import logger


class TaskPlannerService:
    """Decomposes complex healthcare inquiries into structured, verifiable investigation tasks."""

    def plan_tasks(self, research_id: str, query: str) -> List[ResearchTask]:
        """Decompose an overarching inquiry into an initial structured task plan.

        In milestone 1, this constructs the standardized foundational task pipeline
        scaffolding without invoking external AI engines.
        """
        logger.info(f"Generating task plan for research [{research_id}] - Query: '{query[:60]}...'")

        standard_phases = [
            ("Facility Identification", f"Identify hospitals and medical centers relevant to: {query}"),
            ("Capacity & Census Retrieval", "Gather current and historical bed capacity metrics across clinical registries"),
            ("Claim Cross-Verification", "Compare findings across sources to detect contradictions and closure notices"),
            ("Spatial Access & Gap Analysis", "Calculate travel distances and assess regional healthcare accessibility gaps"),
            ("Evidence Dossier Synthesis", "Compile findings, citations, and conflict tables into a structured report"),
        ]

        tasks: List[ResearchTask] = []
        for index, (title, description) in enumerate(standard_phases, start=1):
            tasks.append(
                ResearchTask(
                    research_id=research_id,
                    title=title,
                    description=description,
                    status=TaskStatus.PENDING,
                    order=index,
                )
            )

        return tasks
