# ResearchOps

ResearchOps is a lightweight healthcare-infrastructure research dashboard. It accepts a research question, plans bounded subtasks, searches web sources when configured, extracts source-backed facility/service observations, checks explicit contradictions, performs geographic analysis, and returns a traceable report.

ResearchOps is a research aid, not clinical advice. Missing sources, unavailable coordinates, and single-source findings remain explicitly uncertain. It does not treat absent web results as proof that a service is absent.

## Quick start

Requires Python 3.11 or newer. From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Copy `.env.example` to `.env`. The default local setup uses in-memory storage and mock geocoding; data is lost on restart, and searches are marked `unconfigured` until `TAVILY_API_KEY` is set. To persist data, configure Supabase and apply the SQL migrations in `backend/app/db/migrations/` in numeric order. See [setup](docs/setup.md).

Run the backend and frontend together:

```bash
python scripts/run_dev.py
```

Open <http://127.0.0.1:8000/ui/>. Health check: <http://127.0.0.1:8000/api/health>. Interactive OpenAPI docs: <http://127.0.0.1:8000/docs>.

Run checks:

```bash
python -m ruff check --config backend/pyproject.toml backend scripts
python -m pytest backend/tests -q
```

See [demo instructions](docs/demo.md), [API reference](docs/api.md), [architecture](docs/architecture.md), and [deployment](docs/deployment.md). Setup, database migrations, environment settings, frontend behavior, tests, and production requirements are detailed in [docs/setup.md](docs/setup.md).

## Runtime modes

- `live`: web search is configured and provider results are used. Database persistence is reported separately because live search may be paired with local storage during development.
- `mock`: synthetic/test providers were explicitly injected (primarily automated tests). Mock output must not be presented as real research.
- `unconfigured`: no live search credentials are configured. No web results are fabricated; limitations are returned with the report.

Local database storage without Supabase is process-local memory, not durable persistence. Production configuration rejects mock geocoding, missing Tavily/Supabase credentials, and debug mode.

## Repository layout

```text
backend/app/api/          FastAPI routes and OpenAPI contracts
backend/app/services/     Planning, search, extraction, verification, geo, reports
backend/app/repositories/ Database access adapters
backend/app/db/migrations Supabase/PostgreSQL schema migrations
backend/tests/            Unit, API, and mock-labeled pipeline tests
frontend/                 No-build HTML/CSS/JavaScript dashboard
docs/                     Setup, API, demo, deployment, architecture guides
scripts/run_dev.py        Local development server runner
```
