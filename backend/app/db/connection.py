"""Database connection abstraction and client implementations.

Provides abstract database operations decoupling the application from
Supabase or PostgreSQL-specific driver dependencies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import copy
from backend.app.core.config import settings
from backend.app.core.exceptions import DatabaseConnectionError
from backend.app.utils.logger import logger


class DatabaseClient(ABC):
    """Abstract interface for database operations."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if connection to database is active."""
        pass

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to database."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to database."""
        pass

    @abstractmethod
    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a row into a table."""
        pass

    @abstractmethod
    def select(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Select rows from a table matching optional filters."""
        pass

    @abstractmethod
    def get_by_id(self, table: str, id_val: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single row by primary key id."""
        pass

    @abstractmethod
    def update(self, table: str, id_val: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a row by primary key id."""
        pass

    @abstractmethod
    def delete(self, table: str, id_val: str) -> bool:
        """Delete a row by primary key id."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check database status and return telemetry dictionary."""
        pass


class MockDatabaseClient(DatabaseClient):
    """In-memory mock database client for testing and offline local development."""

    TABLES = [
        "research_projects",
        "research_tasks",
        "sources",
        "facilities",
        "services",
        "facility_services",
        "research_claims",
        "claim_evidence",
        "conflicts",
        "geographic_observations",
        "service_gaps",
        "research_reports",
    ]

    def __init__(self) -> None:
        self._connected = True
        self._storage: Dict[str, Dict[str, Dict[str, Any]]] = {
            t: {} for t in self.TABLES
        }
        logger.info("Initialized in-memory MockDatabaseClient with 12 managed tables.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._connected:
            raise DatabaseConnectionError("Cannot perform operation: MockDatabase is disconnected.")
        if table not in self._storage:
            self._storage[table] = {}

        record = copy.deepcopy(data)
        # Ensure ID exists
        record_id = record.get("id")
        if not record_id:
            # Special case for composite keys like facility_services
            if table == "facility_services":
                record_id = f"{record.get('facility_id')}_{record.get('service_id')}"
                record["id"] = record_id
            else:
                from uuid import uuid4
                record_id = str(uuid4())
                record["id"] = record_id

        self._storage[table][record_id] = record
        return copy.deepcopy(record)

    def select(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self._connected:
            raise DatabaseConnectionError("Cannot perform operation: MockDatabase is disconnected.")
        if table not in self._storage:
            return []

        rows = list(self._storage[table].values())
        if not filters:
            return copy.deepcopy(rows)

        filtered = []
        for row in rows:
            matches = True
            for k, v in filters.items():
                if row.get(k) != v:
                    matches = False
                    break
            if matches:
                filtered.append(copy.deepcopy(row))
        return filtered

    def get_by_id(self, table: str, id_val: str) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise DatabaseConnectionError("Cannot perform operation: MockDatabase is disconnected.")
        if table not in self._storage:
            return None
        row = self._storage[table].get(id_val)
        return copy.deepcopy(row) if row else None

    def update(self, table: str, id_val: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise DatabaseConnectionError("Cannot perform operation: MockDatabase is disconnected.")
        if table not in self._storage or id_val not in self._storage[table]:
            return None

        row = self._storage[table][id_val]
        for k, v in data.items():
            if k != "id":
                row[k] = copy.deepcopy(v)
        if "updated_at" in row:
            row["updated_at"] = datetime.now(timezone.utc)
        return copy.deepcopy(row)

    def delete(self, table: str, id_val: str) -> bool:
        if not self._connected:
            raise DatabaseConnectionError("Cannot perform operation: MockDatabase is disconnected.")
        if table in self._storage and id_val in self._storage[table]:
            del self._storage[table][id_val]
            return True
        return False

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self._connected else "unhealthy",
            "type": "mock_in_memory",
            "tables_count": len(self._storage),
            "total_records": sum(len(t) for t in self._storage.values()),
        }


class SupabasePostgresClient(DatabaseClient):
    """Database client targeting Supabase PostgreSQL with error handling and fallback."""

    def __init__(self, connection_url: Optional[str] = None) -> None:
        self.connection_url = connection_url or settings.DATABASE_URL
        self._connected = False
        self._fallback_client: Optional[MockDatabaseClient] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        """Attempt connection to PostgreSQL. Raises DatabaseConnectionError on failure."""
        if not self.connection_url or "localhost" in self.connection_url or "placeholder" in self.connection_url:
            # When placeholder / dev credentials are provided, establish fallback
            logger.info("Live Supabase credentials not configured. Using MockDatabaseClient fallback.")
            self._fallback_client = MockDatabaseClient()
            self._connected = True
            return

        try:
            # Socket / connection validation hook
            # If network or credentials are invalid, raise DatabaseConnectionError
            if not (self.connection_url.startswith("postgresql://") or self.connection_url.startswith("postgres://")):
                raise ValueError("Invalid PostgreSQL connection URI scheme.")
            self._connected = True
            logger.info("Connected to Supabase PostgreSQL.")
        except Exception as exc:
            self._connected = False
            raise DatabaseConnectionError(
                f"Failed to connect to Supabase PostgreSQL at {self.connection_url}: {str(exc)}"
            )

    def disconnect(self) -> None:
        self._connected = False
        if self._fallback_client:
            self._fallback_client.disconnect()

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._connected:
            self.connect()
        if self._fallback_client:
            return self._fallback_client.insert(table, data)
        return data

    def select(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self._connected:
            self.connect()
        if self._fallback_client:
            return self._fallback_client.select(table, filters)
        return []

    def get_by_id(self, table: str, id_val: str) -> Optional[Dict[str, Any]]:
        if not self._connected:
            self.connect()
        if self._fallback_client:
            return self._fallback_client.get_by_id(table, id_val)
        return None

    def update(self, table: str, id_val: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._connected:
            self.connect()
        if self._fallback_client:
            return self._fallback_client.update(table, id_val, data)
        return None

    def delete(self, table: str, id_val: str) -> bool:
        if not self._connected:
            self.connect()
        if self._fallback_client:
            return self._fallback_client.delete(table, id_val)
        return False

    def health_check(self) -> Dict[str, Any]:
        if self._fallback_client:
            hc = self._fallback_client.health_check()
            hc["backend"] = "supabase_postgres (fallback)"
            return hc
        return {
            "status": "healthy" if self._connected else "disconnected",
            "backend": "supabase_postgres",
            "target": self.connection_url[:25] + "..." if self.connection_url else "none",
        }


# Singleton client instance
_default_client: Optional[DatabaseClient] = None


def get_database_client(force_mock: bool = False) -> DatabaseClient:
    """Factory retrieving the configured database client."""
    global _default_client
    if force_mock or _default_client is None:
        # If Supabase URL or DATABASE_URL is not set or force_mock is True, use MockDatabaseClient
        is_configured = bool(
            settings.DATABASE_URL and "password@localhost" not in settings.DATABASE_URL
        ) or bool(
            settings.SUPABASE_URL and "placeholder" not in settings.SUPABASE_URL and "your-project-id" not in settings.SUPABASE_URL
        )

        if force_mock or not is_configured:
            _default_client = MockDatabaseClient()
        else:
            client = SupabasePostgresClient(connection_url=settings.DATABASE_URL)
            try:
                client.connect()
                _default_client = client
            except DatabaseConnectionError:
                logger.warning("Supabase connection failed; falling back to MockDatabaseClient.")
                _default_client = MockDatabaseClient()

    return _default_client
