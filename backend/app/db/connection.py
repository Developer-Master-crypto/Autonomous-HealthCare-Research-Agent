"""Database connection abstraction and client implementations.

Provides abstract database operations decoupling the application from
Supabase or PostgreSQL-specific driver dependencies.
"""

import copy
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.exceptions import ConfigurationError, DatabaseConnectionError
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

    @abstractmethod
    def persist_bundle(self, records: List[Dict[str, Any]]) -> None:
        """Atomically persist related records or raise a safe database error."""
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

    def persist_bundle(self, records: List[Dict[str, Any]]) -> None:
        if not self._connected:
            raise DatabaseConnectionError("Database operation unavailable.")
        snapshot = copy.deepcopy(self._storage)
        try:
            for item in records:
                table, data = item["table"], item["data"]
                if table == "facility_services":
                    data = {key: value for key, value in data.items() if key != "service_name"}
                if table == "research_projects" and data.get("id") in self._storage[table]:
                    self.update(table, data["id"], data)
                elif table == "sources" and data.get("id") in self._storage[table]:
                    self.update(table, data["id"], data)
                else:
                    self.insert(table, data)
        except Exception:
            self._storage = snapshot
            raise


class SupabasePostgresClient(DatabaseClient):
    """Supabase/PostgREST implementation of the application database port."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        schema: Optional[str] = None,
        client: Any = None,
    ) -> None:
        self.url = url if url is not None else settings.SUPABASE_URL
        self.key = key if key is not None else settings.SUPABASE_SERVICE_ROLE_KEY
        self.schema = schema if schema is not None else settings.SUPABASE_SCHEMA
        self._client = client
        self._connected = client is not None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        """Create the Supabase client without exposing configuration secrets."""
        if self._connected:
            return
        if not self.url or not self.key:
            raise ConfigurationError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured for Supabase access.")
        try:
            from supabase import create_client

            self._client = create_client(self.url, self.key)
            self._connected = True
            logger.info("Initialized Supabase PostgreSQL client.")
        except Exception as exc:
            self._connected = False
            raise DatabaseConnectionError("Failed to initialize the Supabase PostgreSQL client.") from exc

    def disconnect(self) -> None:
        self._connected = False
        self._client = None

    def _table(self, table: str) -> Any:
        if not self._connected:
            self.connect()
        try:
            return self._client.schema(self.schema).table(table) if self.schema != "public" else self._client.table(table)
        except Exception as exc:
            raise DatabaseConnectionError(f"Unable to access database table '{table}'.") from exc

    @staticmethod
    def _data(response: Any) -> List[Dict[str, Any]]:
        data = getattr(response, "data", response)
        return data if isinstance(data, list) else ([] if data is None else [data])

    def _execute(self, operation: Any, table: str) -> List[Dict[str, Any]]:
        try:
            return self._data(operation.execute())
        except Exception as exc:
            self._connected = False
            raise DatabaseConnectionError(f"Database operation failed for table '{table}'.") from exc

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        rows = self._execute(self._table(table).insert(data), table)
        if not rows:
            raise DatabaseConnectionError(f"Insert returned no record for table '{table}'.")
        return rows[0]

    def select(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query = self._table(table).select("*")
        for column, value in (filters or {}).items():
            query = query.eq(column, value)
        return self._execute(query, table)

    def get_by_id(self, table: str, id_val: str) -> Optional[Dict[str, Any]]:
        rows = self._execute(self._table(table).select("*").eq("id", id_val).limit(1), table)
        return rows[0] if rows else None

    def update(self, table: str, id_val: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rows = self._execute(self._table(table).update(data).eq("id", id_val), table)
        return rows[0] if rows else None

    def delete(self, table: str, id_val: str) -> bool:
        rows = self._execute(self._table(table).delete().eq("id", id_val), table)
        return bool(rows)

    def health_check(self) -> Dict[str, Any]:
        try:
            self._execute(self._table("research_projects").select("id").limit(1), "research_projects")
            return {"status": "healthy", "backend": "supabase_postgres"}
        except (ConfigurationError, DatabaseConnectionError):
            return {"status": "unhealthy", "backend": "supabase_postgres"}

    def persist_bundle(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        if not self._connected:
            self.connect()
        try:
            rpc_client = self._client if self.schema == "public" else self._client.schema(self.schema)
            rpc_client.rpc("persist_research_bundle", {"p_records": records}).execute()
        except Exception as exc:
            self._connected = False
            raise DatabaseConnectionError("Atomic research record persistence failed.") from exc


# Singleton client instance
_default_client: Optional[DatabaseClient] = None


def get_database_client(force_mock: bool = False) -> DatabaseClient:
    """Factory retrieving the configured database client."""
    global _default_client
    if force_mock or _default_client is None:
        is_configured = bool(
            settings.SUPABASE_URL
            and settings.SUPABASE_SERVICE_ROLE_KEY
            and "your-project-id" not in settings.SUPABASE_URL
            and "placeholder" not in settings.SUPABASE_SERVICE_ROLE_KEY
        )

        if force_mock or not is_configured:
            _default_client = MockDatabaseClient()
        else:
            client = SupabasePostgresClient()
            try:
                client.connect()
                _default_client = client
            except DatabaseConnectionError:
                logger.warning("Supabase connection failed; database operations remain unavailable.")
                _default_client = client

    return _default_client
