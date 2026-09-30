"""Repositories for facilities, analysis entities, and reports."""

from typing import List, Optional

from backend.app.db.connection import DatabaseClient
from backend.app.models.db_models import (
    ConflictModel,
    FacilityModel,
    FacilityServiceModel,
    GeographicObservationModel,
    ResearchReportModel,
    ServiceGapModel,
    ServiceModel,
)
from backend.app.repositories.base import BaseRepository


class FacilityRepository(BaseRepository[FacilityModel]):
    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(FacilityModel, "facilities", db_client)


class ServiceRepository(BaseRepository[ServiceModel]):
    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(ServiceModel, "services", db_client)


class FacilityServiceRepository(BaseRepository[FacilityServiceModel]):
    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(FacilityServiceModel, "facility_services", db_client)

    def get_for_facility(self, facility_id: str) -> List[FacilityServiceModel]:
        return self.filter({"facility_id": facility_id})


class ConflictRepository(BaseRepository[ConflictModel]):
    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(ConflictModel, "conflicts", db_client)

    def get_for_project(self, project_id: str) -> List[ConflictModel]:
        return self.filter({"research_project_id": project_id})


class GeographicObservationRepository(BaseRepository[GeographicObservationModel]):
    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(GeographicObservationModel, "geographic_observations", db_client)


class ServiceGapRepository(BaseRepository[ServiceGapModel]):
    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(ServiceGapModel, "service_gaps", db_client)

    def get_for_project(self, project_id: str) -> List[ServiceGapModel]:
        return self.filter({"research_project_id": project_id})


class ResearchReportRepository(BaseRepository[ResearchReportModel]):
    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(ResearchReportModel, "research_reports", db_client)

    def get_for_project(self, project_id: str) -> List[ResearchReportModel]:
        return self.filter({"research_project_id": project_id})
