# BudgetDiff

[![CI](https://github.com/gokubuilds/Budgetdiff/actions/workflows/ci.yml/badge.svg)](https://github.com/gokubuilds/Budgetdiff/actions/workflows/ci.yml)

> Know exactly what changed between Union Budget estimates, revised figures and actuals, year by year.

## Project Overview

Every Union Budget scheme has a Budget Estimate (BE), a Revised Estimate (RE) the next year, and Actuals two years later, spread across complex Expenditure Budget and Demand for Grants documents. Researchers frequently quote an old estimate as if it were final, and finding what changed between interim and full budgets can take days.

**BudgetDiff** tracks central allocations across all budget stages, enabling instant diffing between versions and ensuring policy researchers and journalists always work with verified, cited figures.

- **Target Audience**: Policy researchers, economic analysts, and journalists tracking central government spending on education, health, agriculture, and rural development schemes.
- **Signature Feature**: Version timeline per scheme showing BE, RE, and Actuals year-by-year with arrows indicating spending cuts or increases.
- **Core Problem Solved**: Multi-stage budget versioning (BE vs. RE vs. Actuals vs. Interim) with transparent citations.
- **Cost Documentation**: See [docs/COST.md](docs/COST.md) for detailed LLM token economics and cost-reduction strategies.
- **Target Questions**: See [docs/QUESTIONS.md](docs/QUESTIONS.md) for 10 representative policy research queries.

---

## Architecture

BudgetDiff integrates a resilient FastAPI service with Google Gemini LLM orchestration, structured SQLite/PostgreSQL persistence, and pgvector readiness:

```
[ Client / Researcher ]
          |
          v (HTTP)
[ FastAPI Backend ] 
    ├── GET /health  ──> Instant liveness probe (no DB/LLM dependency)
    ├── GET /ready   ──> Database connectivity check (SELECT 1)
    ├── GET /usage   ──> Token consumption & financial cost reporting
    └── POST /chat   ──> Primary model (gemini-1.5-pro)
                              │ (retry on 429/5xx/timeout)
                              ▼
                         Fallback model (gemini-1.5-flash)
                              │
                              ▼
                         Audit Logging (logs/cost.jsonl & usage_logs table)
```

- **Primary Model**: `gemini-1.5-pro` with exponential backoff retry for transient errors.
- **Fallback Model**: `gemini-1.5-flash` (`LLM_FALLBACK_MODEL`) triggered safely when provider is unavailable.
- **Database**: PostgreSQL 16 with `pgvector` enabled for local Docker; SQLite for lightweight local runs.

---

## Run Locally

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Configure environment variables
cp .env.example .env            # On Windows: copy .env.example .env

# 4. Start API server
uvicorn app.main:app --reload

# 5. Test endpoints
curl localhost:8000/health
curl localhost:8000/ready
curl -X POST localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "What is PM-KISAN BE?"}'
curl localhost:8000/usage
```

---

## Run with Docker

To run the complete production stack (FastAPI + PostgreSQL + pgvector):

```bash
# 1. Copy configuration
cp .env.example .env            # On Windows: copy .env.example .env

# 2. Build and launch services
docker compose up --build

# 3. Verify database readiness
curl localhost:8000/ready

# 4. Verify API liveness
curl localhost:8000/health
```

Interactive Swagger documentation is accessible at `http://localhost:8000/docs`.

---

## API Endpoints

| Method | Path | Description | Expected Status |
|---|---|---|---|
| `GET` | `/health` | Fast process liveness probe. Independent of database or LLM. | `200 OK` |
| `GET` | `/ready` | Database readiness check (`SELECT 1`). Fails with 503 if database is stopped. | `200 OK` / `503 Service Unavailable` |
| `POST` | `/chat` | Conversational LLM query with retry, fallback, and streaming support. | `200 OK` / `422` / `500` |
| `GET` | `/usage` | Aggregated token usage, dollar cost, model breakdown, and daily stats. | `200 OK` |

---

## CI & Automated Testing

Automated testing and container verification run on every push via GitHub Actions:
- **Linting**: Ruff formatting and syntax verification (`ruff check .`).
- **Tests**: Pytest suite using offline `FakeLLMProvider` (no external API keys required).
- **Docker Smoke Test**: Builds the container image and verifies `GET /health` inside Docker.

---

## Live Deployment

The service is configured for container deployment on Render's free tier via `render.yaml`:

- **Deployment Blueprint**: `render.yaml`
- **Target Service**: `https://budgetdiff-api.onrender.com`
- **Health Check**: `https://budgetdiff-api.onrender.com/health`
- **Usage Metrics**: `https://budgetdiff-api.onrender.com/usage`

*(Note: Live deployment is provisioned from the GitHub repository using the Render Blueprint specification. If first deploying via the Render web dashboard, select **New + -> Blueprint** and connect the `gokubuilds/Budgetdiff` repository).*
