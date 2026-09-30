# Local setup and operations

## Requirements

- Python 3.11+
- pip and a modern browser
- Optional for live research: Tavily API key
- Optional for durable storage: Supabase project with PostgreSQL/PostgREST access

There is no Node frontend build. FastAPI serves the dashboard and API from one origin.

## Install

From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

Create local settings:

```bash
cp .env.example .env
# PowerShell: Copy-Item .env.example .env
```

Only put secrets in the ignored `.env` file or your deployment secret manager. Never put backend keys in `frontend/`.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `ENVIRONMENT` | No; `development` | Use `production` to enable fail-fast production configuration checks. |
| `DEBUG` | No; `true` | Enables development reload in `scripts/run_dev.py`; must be false in production. |
| `PROJECT_NAME`, `VERSION` | No | API metadata. |
| `API_HOST`, `API_PORT` | No | Local runner bind address and port; defaults to `127.0.0.1:8000`. |
| `ALLOWED_ORIGINS` | No | Comma-separated exact browser origins. Wildcards, paths, and credentials in origins are rejected. |
| `SUPABASE_URL`, `SUPABASE_KEY` | Optional locally; required in production | Server-only Supabase project URL and key. Never expose the key to the browser. |
| `SUPABASE_SCHEMA` | No; `public` | Database schema name. |
| `TAVILY_API_KEY` | Optional locally; required in production | Enables external source search. Without it the run is `unconfigured`, not a mock success. |
| `SEARCH_TIMEOUT_SECONDS` | No; `15` | Provider timeout, range 0–60 exclusive of zero. |
| `SEARCH_MAX_RESULTS` | No; `10` | Results per search, 1–20. |
| `SOURCE_FETCH_TIMEOUT_SECONDS` | No; `15` | Source page fetch timeout. |
| `MAX_SOURCE_CONTENT_CHARS` | No; `12000` | Maximum extracted page text size, 1–100000 characters. |
| `RESEARCH_RATE_LIMIT_PER_MINUTE` | No; `20` | Per-process request cap, 1–600. |
| `GEOCODING_PROVIDER` | No locally; `mock` | `mock` uses a limited local lookup; production requires `nominatim`. Unknown places stay unresolved. |

`DATABASE_URL`, LLM keys, SERPAPI keys, and `SEARCH_PROVIDER` are not consumed by this application and are intentionally not advertised in the environment template. The default planner is deterministic and does not call an LLM.

## Database setup

Without `SUPABASE_URL` and `SUPABASE_KEY`, local development uses an in-memory adapter. Records disappear when the process exits; the API reports `persistence_status: mock_memory`.

For durable storage:

1. Create a Supabase project and restrict database access to the backend.
2. In the Supabase SQL editor, execute `backend/app/db/migrations/001_initial_schema.sql` through `004_add_source_extraction_fields.sql` in numeric order.
3. Configure `SUPABASE_URL`, `SUPABASE_KEY`, and (if needed) `SUPABASE_SCHEMA` in the backend environment. Use a server-side key and do not expose it to the frontend.
4. Verify the table setup with the health route and a small research request; check `persistence_status` in the response and records in `research_projects`, `research_tasks`, `sources`, and `research_reports`.

Review Supabase grants/Row Level Security for your project and use least privilege. The migrations create schema objects but do not establish a deployment-specific authorization policy. A Supabase key alone is not a substitute for appropriate database permissions.

## API setup

Start the app from the repository root:

```bash
python scripts/run_dev.py
```

The runner reads `API_HOST`, `API_PORT`, and `DEBUG`. Alternatively:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Check `GET /api/health`; OpenAPI UI is at `/docs` and the raw schema at `/openapi.json`. Route details are in [api.md](api.md).

## Frontend setup and verification

Open <http://127.0.0.1:8000/ui/> while the API is running. The UI is served by FastAPI, uses same-origin API requests, and requires no npm install/build. It loads Chart.js and Leaflet from public CDNs and OpenStreetMap map tiles. Opening `frontend/index.html` as a `file://` URL is not supported; it will not use the app's same-origin API setup.

If hosting the frontend separately, configure a reverse proxy to route `/api` to FastAPI and serve the UI under that same origin, or update the frontend API base and allow the exact origin in `ALLOWED_ORIGINS` as a separately reviewed deployment change.

## Tests and lint

```bash
python -m ruff check --config backend/pyproject.toml backend scripts
python -m pytest backend/tests -q
```

The end-to-end test uses explicitly labeled synthetic search/page/geocoder adapters. It verifies API stage flow, identifiers, contradiction retention, source links, and in-memory persistence; it is not evidence of live provider or production database connectivity.

## Further reading

- [API reference](api.md)
- [Demo walkthrough](demo.md)
- [Deployment checklist](deployment.md)
- [Architecture and known limitations](architecture.md)
