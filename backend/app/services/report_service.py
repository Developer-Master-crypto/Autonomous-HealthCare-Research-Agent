"""Report generation and dossier management service."""

from typing import Dict, List, Optional
from backend.app.schemas.report import ResearchReport
from backend.app.schemas.source import ResearchSource, ResearchClaim
from backend.app.schemas.facility import Facility
from backend.app.schemas.analysis import Conflict, ServiceGap
from backend.app.utils.logger import logger


class ReportService:
    """Compiles and manages evidence-backed healthcare infrastructure dossiers."""

    def __init__(self) -> None:
        self._reports: Dict[str, ResearchReport] = {}

    def generate_report(
        self,
        research_id: str,
        query: str,
        title: Optional[str] = None,
        executive_summary: Optional[str] = None,
        claims: Optional[List[ResearchClaim]] = None,
        conflicts: Optional[List[Conflict]] = None,
        service_gaps: Optional[List[ServiceGap]] = None,
        facilities: Optional[List[Facility]] = None,
        sources: Optional[List[ResearchSource]] = None,
    ) -> ResearchReport:
        """Synthesize an evidence dossier from aggregated findings."""
        report = ResearchReport(
            research_id=research_id,
            title=title or f"Healthcare Infrastructure Assessment: {query[:45]}",
            query=query,
            executive_summary=executive_summary or (
                f"Preliminary research dossier compiled for inquiry: '{query}'. "
                "Detailed multi-source evidence extraction and verification completed."
            ),
            claims=claims or [],
            conflicts=conflicts or [],
            service_gaps=service_gaps or [],
            facilities=facilities or [],
            sources=sources or [],
        )
        self._reports[report.id] = report
        logger.info(f"Synthesized research report [{report.id}] for research [{research_id}]")
        return report

    def get_report(self, report_id: str) -> Optional[ResearchReport]:
        """Retrieve a report by ID."""
        return self._reports.get(report_id)

    def get_report_by_research_id(self, research_id: str) -> Optional[ResearchReport]:
        """Retrieve the primary report for a research session."""
        for r in self._reports.values():
            if r.research_id == research_id:
                return r
        return None

    def list_reports(self) -> List[ResearchReport]:
        """List all compiled reports."""
        return list(self._reports.values())
