# HTTP API reference

Base path: `/api`. All endpoints accept/return JSON unless noted. The FastAPI-generated OpenAPI schema at `/openapi.json` and Swagger UI at `/docs` are the canonical runtime contracts.

## Health

### `GET /api/health`

Returns `200` with `{"status":"ok","service":"researchops-api"}`. This is a liveness response; it does not prove search or database connectivity.

### `GET /api/health/database`

Returns sanitized adapter connectivity. Without Supabase configuration, the local response identifies the in-memory adapter; configured Supabase returns `healthy` only when the `research_projects` table is reachable.

## Research

### `POST /api/research`

Creates and executes a research run; returns `201` and a `ResearchResponse`.

Request:

```json
{
  "query": "Analyze cardiac healthcare infrastructure within 10 km of Whitefield and identify potential service gaps.",
  "region": null,
  "parameters": {"max_tasks": 5}
}
```

- `query`: required string, 5–4000 characters.
- `region`: optional string, up to 300 characters. If omitted, a simple “within N km of LOCATION” phrase may supply the location and radius.
- `parameters.max_tasks`: optional bounded integer (1–10; default 10).
- `parameters.max_follow_up_tasks`: optional bounded integer (0–2; default 2).

`ResearchResponse` includes `research_id`, `query`, `region`, `status`, `execution_mode`, planned `tasks`, `progress`, `missing_information`, `intermediate_results`, `report_id`, and timestamps. `progress.completed_stages` and `progress.skipped_stages` distinguish work actually performed from unavailable work. `execution_mode` is `live`, explicitly injected `mock`, or `unconfigured`. `intermediate_results.persistence_status` distinguishes `database`, `mock_memory`, and `unavailable`.

### `GET /api/research`

Lists current process-memory research sessions. Does not restore projects from the database after a restart.

### `GET /api/research/{research_id}` and `GET /api/research/{research_id}/status`

Return the current project/progress for an ID held by this process; `404` if it is not available in process memory.

### `GET /api/research/{research_id}/geographic-analysis`

Returns target coordinates/provenance, radius, map-ready facility records, distances, and warnings. Coordinates can be `null` or analysis can be unavailable; they are never guessed. Returns `404` if no geographic result was produced.

### `GET /api/research/{research_id}/report`

Returns the report by research ID, including claims, conflicts, facilities, sources, and report timestamp. Source references use source IDs and original URLs. Returns `404` when the project/report is unavailable in the current process.

## Sources and catalogs

- `GET /api/sources` and `GET /api/sources/{source_id}` — registered source-service records.
- `GET /api/facilities` and `GET /api/facilities/{facility_id}` — in-process geographic facility registry.
- `GET /api/analysis` — current service-level analysis overview.
- `GET /api/analysis/conflicts` — current conflict-service entries.
- `GET /api/analysis/gaps` — current gap-service entries.
- `GET /api/reports` and `GET /api/reports/{report_id}` — current process-memory reports.

The source/facility/analysis catalog endpoints are process-local service registries; they are not complete database-backed query interfaces. Use the per-research report and geographic-analysis routes for results from a particular run.

## Errors and limits

- `422 VALIDATION_ERROR`: invalid/missing request fields; sensitive or oversized query content is not echoed.
- `404 HTTP_404`: project, report, source, or facility is not available.
- `429`: research request limit reached; response includes `Retry-After`.
- `413`: request payload exceeds the 1 MB request limit.
- `500 INTERNAL_SERVER_ERROR`: sanitized unexpected failure.

Most error responses use an `error` object with a stable `code` and safe `message`. Research stage failures are generally returned as project state and limitations rather than exposing provider exception details.

## Security

The API currently has no built-in user authentication or authorization. Do not expose it directly to the public internet. Put it behind an authenticated gateway/private network, TLS-terminating reverse proxy, and appropriately restrictive CORS/database policies before deployment. CORS is not an authentication control.
