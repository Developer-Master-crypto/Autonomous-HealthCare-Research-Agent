# ResearchOps — The Autonomous Healthcare Research Agent

[![Hackathon: GATEWAYS 2026](https://img.shields.io/badge/Hackathon-GATEWAYS_2026-blue.svg)](https://github.com/)
[![Team: Spideyx](https://img.shields.io/badge/Team-Spideyx-green.svg)](https://github.com/)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Frontend: Vanilla JS](https://img.shields.io/badge/Frontend-HTML5_%2F_CSS3_%2F_Vanilla_JS-F7DF1E.svg?logo=javascript&logoColor=black)](https://developer.mozilla.org)

> **ResearchOps** is an autonomous healthcare infrastructure research platform designed to accept natural-language queries, autonomously decompose them into discrete research sub-tasks, aggregate findings across heterogeneous public and clinical registries, detect contradictory claims, identify geographic/service accessibility gaps, and synthesize comprehensive, evidence-backed reports.

---

## 🌟 Hackathon Project Details

- **Project Name:** ResearchOps
- **Team:** Spideyx
- **Event:** GATEWAYS 2026
- **Current Milestone:** Milestone 1 — Project Foundation & Architecture Setup

---

## 🏗️ Architecture & Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript | Ultra-lightweight, zero-build dashboard interface with real-time API monitoring and responsive UX |
| **Backend API** | FastAPI (Python 3.11+) & Uvicorn | High-performance asynchronous REST API gateway with structured schemas, CORS, and centralized error handling |
| **Data Layer** | Supabase / PostgreSQL (`pgvector`) | Relational research registry, citation store, and vector embeddings for semantic literature matching |
| **AI Integration** | Provider-Agnostic LLM Abstraction | Pluggable interface supporting Gemini, OpenAI, Anthropic, or local LLMs without vendor lock-in |
| **Testing** | Pytest, HTTPX | Asynchronous integration and unit testing suite |

For in-depth architectural blueprints, agent state machines, and data schemas, see [docs/architecture.md](docs/architecture.md).

---

## 📁 Project Directory Structure

```text
ResearchOps/
├── .env.example              # Environment variables template (no secrets)
├── .gitignore                 # Standard Python/Web version control exclusions
├── README.md                  # Project overview, team details, and setup guide
├── backend/
│   ├── app/
│   │   ├── api/               # API route handlers & endpoints
│   │   │   ├── __init__.py
│   │   │   ├── health.py      # Health-check endpoint (/api/health)
│   │   │   └── router.py      # Main API router registry
│   │   ├── core/              # Global application configuration & error handling
│   │   │   ├── __init__.py
│   │   │   ├── config.py      # Pydantic Settings & environment loader
│   │   │   └── exceptions.py  # Global exception classes & handlers
│   │   ├── models/            # Database and entity models (Supabase/Postgres)
│   │   │   └── __init__.py
│   │   ├── schemas/           # Pydantic request/response data contracts
│   │   │   ├── __init__.py
│   │   │   └── health.py      # Schema for /api/health response
│   │   ├── services/          # Business logic & external service abstractions
│   │   │   ├── __init__.py
│   │   │   └── llm_base.py    # Provider-agnostic LLM interface
│   │   ├── utils/             # Helper utilities and structured logging
│   │   │   ├── __init__.py
│   │   │   └── logger.py      # Logging formatter and handler
│   │   ├── __init__.py
│   │   └── main.py            # FastAPI application factory and entry point
│   ├── tests/                 # Automated test suite
│   │   ├── __init__.py
│   │   ├── conftest.py        # Pytest client fixtures and test settings
│   │   └── test_health.py     # Health-check endpoint tests
│   ├── pyproject.toml         # Build tool metadata and dependencies
│   └── requirements.txt       # Pinned production and test dependencies
├── docs/
│   └── architecture.md        # Technical architecture & multi-agent pipeline specification
├── frontend/
│   ├── css/
│   │   └── style.css          # Modern dark-mode responsive styles
│   ├── js/
│   │   └── app.js             # Vanilla JS client logic & async fetch handlers
│   └── index.html             # ResearchOps web dashboard entry point
└── scripts/
    └── run_dev.py             # Cross-platform developer launch runner
```

---

## 🚀 Getting Started Locally

### Prerequisites

- **Python 3.11+** installed (verified compatible up to 3.13)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### 1. Environment Setup

Clone the repository and navigate into the project directory:

```bash
cd Antigravity
```

Create and activate a Python virtual environment:

**On Windows (PowerShell):**
```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables

Copy the example configuration to create your local `.env`:

```bash
cp .env.example .env
```
*(On Windows PowerShell, use `Copy-Item .env.example .env`)*

### 4. Run the Automated Tests

Verify that the backend environment and health endpoint pass all test checks:

```bash
pytest backend/tests -v
```

### 5. Start the FastAPI Backend Server

Run the development server using Uvicorn:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Alternatively, use the developer runner script:
```bash
python scripts/run_dev.py
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive API Documentation (Swagger): `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/api/health`

### 6. Launch the Frontend

Open `frontend/index.html` directly in your browser, or serve it using Python's built-in HTTP server:

```bash
python -m http.server 3000 --directory frontend
```

Visit `http://127.0.0.1:3000` to interact with the ResearchOps dashboard and test the real-time API health connection.

---

## 🔍 Health-Check API Specification

### Endpoint: `GET /api/health`

**Success Response (200 OK):**
```json
{
  "status": "ok",
  "service": "researchops-api"
}
```

---

## 🗺️ Project Roadmap & Next Milestones

- [x] **Milestone 1:** Project Foundation, Health Check API & Test Suite (Current)
- [ ] **Milestone 2:** Provider-Agnostic LLM Engine (Gemini / Anthropic / OpenAI connectors)
- [ ] **Milestone 3:** Autonomous Query Decomposition Agent & Task Planner
- [ ] **Milestone 4:** Multi-Source Data Gathering & Web Retrieval Connectors
- [ ] **Milestone 5:** Entity Extraction, Conflict Detection & Reconciliation Agent
- [ ] **Milestone 6:** Healthcare Geographic & Service-Gap Analysis Engine
- [ ] **Milestone 7:** Evidence-Backed Synthesis & Exportable Research Report Generator

---

## 👥 Team Spideyx — GATEWAYS 2026

Built with dedication for GATEWAYS 2026.
