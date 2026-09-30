"""Verification and conflict detection service."""

from typing import Dict, List, Optional
from backend.app.schemas.source import ResearchClaim, ResearchSource
from backend.app.schemas.analysis import Conflict, ConflictStatus
from backend.app.utils.logger import logger


class VerificationService:
    """Detects discrepancies between independent healthcare assertions and manages conflict state."""

    def __init__(self) -> None:
        self._conflicts: Dict[str, Conflict] = {}

    def flag_conflict(
        self,
        topic: str,
        claim_a: ResearchClaim,
        claim_b: ResearchClaim,
        description: str,
        status: ConflictStatus = ConflictStatus.UNRESOLVED,
    ) -> Conflict:
        """Register a contradiction detected between two distinct evidence claims."""
        conflict = Conflict(
            topic=topic,
            claim_a=claim_a,
            claim_b=claim_b,
            description=description,
            resolution_status=status,
        )
        self._conflicts[conflict.id] = conflict
        logger.warning(f"Evidentiary conflict flagged on topic '{topic}': {description}")
        return conflict

    def list_conflicts(self) -> List[Conflict]:
        """List all detected evidentiary conflicts."""
        return list(self._conflicts.values())

    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """Retrieve a specific conflict by ID."""
        return self._conflicts.get(conflict_id)
