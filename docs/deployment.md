# Deployment guide and readiness limits

ResearchOps has no bundled container image, migration runner, frontend build, or authentication layer. Deploy the ASGI app behind infrastructure you operate; do not make it a public unauthenticated endpoint.

## Required production configuration

Provide settings through your platform's secret manager/environment, not a committed `.env`:

```text
ENVIRONMENT=production
DEBUG=false
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<server-side key>
SUPABASE_SCHEMA=public
TAVILY_API_KEY=<provider key>
GEOCODING_PROVIDER=nominatim
ALLOWED_ORIGINS=https://<your-demo-host>
```

Production configuration fails fast when debug is on, Supabase credentials are missing/placeholder, Tavily is not configured, or mock geocoding is selected. Search, fetch, content, rate-limit, and source-size values may be set using the variable names in [setup.md](setup.md). Never place provider/database secrets in JavaScript, HTML, or client-side environment variables.

## Database

Provision a Supabase project, apply SQL migrations `001` through `004` in order, and verify grants/RLS and schema access for the backend identity. Use least privilege and keep the key server-side. The app uses Supabase/PostgREST; `DATABASE_URL` is not read. Without working DB access, requests may run with explicit persistence errors, so check `persistence_status` and logs after deployment.

## Network and process

1. Build/release the Python environment from `backend/requirements.txt`.
2. Start one API process without auto-reload:

   ```bash
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1
   ```

3. Put it behind a TLS reverse proxy and authenticated gateway/private network. Restrict origins to the deployed UI origin; CORS alone does not protect the API.
4. Route `/api/*`, `/docs` (if enabled), and `/ui/*` to the backend, or disable public access to docs at the proxy.
5. Set the platform health probe to `GET /api/health`; it is a liveness check, not a dependency/readiness check.
6. Keep outbound access narrowly scoped to Supabase, Tavily, public source pages, Nominatim, and map/CDN assets as required. Apply timeouts and egress controls.

Use one process/replica for the current implementation: request throttling, project/report lookup, and several registries are process-local. Multiple workers or replicas can produce inconsistent lookups and per-worker limits. Database records do not yet provide API recovery after restart.

## Frontend

FastAPI serves the no-build UI at `/ui/`. Chart.js and Leaflet load from public CDNs, and map tiles use OpenStreetMap. Check the browser console, CSP, proxy routes, and outbound browser network policy if charts or map tiles fail. The UI makes same-origin requests; for a separate UI host, configure a deliberate API base/proxy and exact CORS origin before deployment.

## Pre-release checks

```bash
python -m ruff check --config backend/pyproject.toml backend scripts
python -m pytest backend/tests -q
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Then verify `/api/health`, `/docs`, `/ui/`, a live research run with provider credentials, original source URLs, database persistence status and rows, no secrets in responses/logs, and graceful provider/database failure behavior. The automated pipeline test is explicitly mock mode and does not replace these live checks.

## Not yet production-complete

- No built-in API authentication/authorization.
- Research/report retrieval state and rate limits are process-local; DB-backed recovery and shared throttling are not implemented.
- Health is liveness-only; there is no dependency readiness endpoint.
- LLM planning is not connected to the default orchestrator.
- Review external provider terms, data handling, geocoding usage limits, Supabase authorization, retention, backups, and observability for your deployment.
