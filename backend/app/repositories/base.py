"""Generic base repository defining standard data access interface."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

from backend.app.db.connection import DatabaseClient, get_database_client

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Generic repository providing decoupled CRUD operations against the database abstraction."""

    def __init__(self, model_class: Type[T], table_name: str, db_client: Optional[DatabaseClient] = None) -> None:
        self.model_class = model_class
        self.table_name = table_name
        self.db_client = db_client or get_database_client()

    def get_by_id(self, id_val: str) -> Optional[T]:
        """Fetch a single record by primary key."""
        row = self.db_client.get_by_id(self.table_name, id_val)
        if not row:
            return None
        return self.model_class.model_validate(row)

    def list_all(self) -> List[T]:
        """Fetch all records in the table."""
        rows = self.db_client.select(self.table_name)
        return [self.model_class.model_validate(r) for r in rows]

    def filter(self, filters: Dict[str, Any]) -> List[T]:
        """Filter records by attribute equality."""
        rows = self.db_client.select(self.table_name, filters)
        return [self.model_class.model_validate(r) for r in rows]

    def create(self, entity: T) -> T:
        """Insert a new entity record."""
        data = entity.model_dump(mode="json")
        inserted = self.db_client.insert(self.table_name, data)
        return self.model_class.model_validate(inserted)

    def update(self, id_val: str, data: Dict[str, Any]) -> Optional[T]:
        """Update an existing entity record."""
        updated = self.db_client.update(self.table_name, id_val, data)
        if not updated:
            return None
        return self.model_class.model_validate(updated)

    def delete(self, id_val: str) -> bool:
        """Delete an entity by primary key."""
        return self.db_client.delete(self.table_name, id_val)
