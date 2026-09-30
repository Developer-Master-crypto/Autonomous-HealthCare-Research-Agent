"""Tests for the provider-independent ResearchOps database layer."""

import pytest

from backend.app.core.exceptions import ConfigurationError, DatabaseConnectionError
from backend.app.db.connection import MockDatabaseClient, SupabasePostgresClient
from backend.app.models.db_models import FacilityModel, ResearchProjectModel, ServiceModel
from backend.app.repositories import (
    FacilityRepository,
    ResearchProjectRepository,
    ServiceRepository,
)


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, response):
        self.response = response
        self.filters = []

    def select(self, _columns):
        return self

    def insert(self, _data):
        return self

    def update(self, _data):
        return self

    def delete(self):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, _value):
        return self

    def execute(self):
        return FakeResponse(self.response)


class FakeSupabaseClient:
    def __init__(self, response):
        self.response = response
        self.table_name = None

    def table(self, table_name):
        self.table_name = table_name
        return FakeQuery(self.response)

    def rpc(self, name, params):
        self.rpc_name = name
        self.rpc_params = params
        return FakeQuery(None)


def test_repositories_operate_against_mock_database_without_credentials():
    database = MockDatabaseClient()
    project = ResearchProjectRepository(database).create(
        ResearchProjectModel(user_query="Find rural trauma services")
    )
    facility = FacilityRepository(database).create(FacilityModel(name="North County Hospital"))
    service = ServiceRepository(database).create(ServiceModel(name="Trauma care"))

    assert ResearchProjectRepository(database).get_by_id(project.id) == project
    assert FacilityRepository(database).get_by_id(facility.id) == facility
    assert ServiceRepository(database).get_by_id(service.id) == service


def test_mock_database_reports_connection_errors_after_disconnect():
    database = MockDatabaseClient()
    database.disconnect()

    with pytest.raises(DatabaseConnectionError):
        database.select("research_projects")


def test_mock_bundle_is_atomic_on_failure():
    database = MockDatabaseClient()
    with pytest.raises(Exception):
        database.persist_bundle([
            {"table": "research_projects", "data": {"id": "project-a", "user_query": "query"}},
            {"table": "research_tasks"},
        ])
    assert database.get_by_id("research_projects", "project-a") is None


def test_supabase_adapter_uses_supabase_operations_via_the_port():
    fake_client = FakeSupabaseClient([{"id": "project-1", "user_query": "Test", "status": "pending"}])
    database = SupabasePostgresClient(client=fake_client)

    record = database.insert("research_projects", {"user_query": "Test"})
    selected = database.select("research_projects", {"status": "pending"})

    assert record["id"] == "project-1"
    assert selected[0]["user_query"] == "Test"
    assert fake_client.table_name == "research_projects"


def test_supabase_adapter_requires_configuration_when_no_client_is_injected():
    database = SupabasePostgresClient(url="", key="")

    with pytest.raises(ConfigurationError):
        database.connect()


def test_supabase_bundle_uses_atomic_rpc():
    client = FakeSupabaseClient([])
    database = SupabasePostgresClient(client=client)
    bundle = [{"table": "research_tasks", "data": {"id": "task-a"}}]
    database.persist_bundle(bundle)
    assert client.rpc_name == "persist_research_bundle"
    assert client.rpc_params == {"p_records": bundle}


def test_configured_database_failure_does_not_switch_to_ephemeral_mock(monkeypatch):
    import backend.app.db.connection as connection
    from backend.app.core.config import settings

    monkeypatch.setattr(connection, "_default_client", None)
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://database.example")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "configured-key")
    monkeypatch.setattr(SupabasePostgresClient, "connect", lambda self: (_ for _ in ()).throw(DatabaseConnectionError("unavailable")))
    database = connection.get_database_client()
    assert isinstance(database, SupabasePostgresClient)
    assert not database.is_connected
    monkeypatch.setattr(connection, "_default_client", None)
