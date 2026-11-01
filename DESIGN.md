# BudgetDiff System Design

## 1. System Overview

**BudgetDiff** enables policy researchers to track, verify, and compare figures across Union Budget stages:
- **Budget Estimate (BE)**
- **Revised Estimate (RE)**
- **Actuals**
- **Interim vs. Full Budget variations**

The system couples a high-performance **FastAPI** backend with **Google Gemini LLM orchestration**, **pgvector/PostgreSQL** for database persistence and readiness probing, and transparent cost telemetry.

### Architecture

```
                           +------------------------+
                           |  Client / Policy User  |
                           +-----------+------------+
                                       |
                POST /chat, GET /health, GET /ready, GET /usage
                                       v
                      +----------------------------------+
                      |        BudgetDiff FastAPI        |
                      +-----------------+----------------+
                                       |
                 +---------------------+---------------------+
                 |                                           |
                 v                                           v
     +-----------------------+                   +-----------------------+
     |   LLM Orchestrator    |                   |    Database Layer     |
     |                       |                   |                       |
     | 1. Primary Model:     |                   | - SQLite (local / CI) |
     |    gemini-1.5-pro     |                   | - PostgreSQL+pgvector |
     |    (with retry logic) |                   |   (Docker / Prod)     |
     |                       |                   |                       |
     | 2. Fallback Model:    |                   | Actual Tables:        |
     |    gemini-1.5-flash   |                   | - usage_logs          |
     |    (on LLMUnavailable)|                   |                       |
     |                       |                   | Checks:               |
     | 3. Cost & Telemetry   |                   | - SELECT 1 (/ready)   |
     |    - logs/cost.jsonl  |                   | - pgvector enabled    |
     +-----------+-----------+                   +-----------------------+
                 |
                 v
     +-----------------------+
     | Google Gemini API     |
     | (FakeLLM in test/CI)  |
     +-----------------------+
```

---

## 2. API Endpoints

### 2.1 `GET /health`
Liveness probe. Fast check indicating the API process is alive and receiving traffic.
- **Method**: `GET`
- **Path**: `/health`
- **Purpose**: Liveness probe for Docker, orchestrators, and load balancers. Does NOT query the database or external LLMs. Remains 200 even when database is stopped.
- **Request**: None
- **Response (`200 OK`)**:
```json
{
  "status": "ok",
  "app": "BudgetDiff",
  "environment": "production"
}
```
- **Error Codes**: `500 Internal Server Error` if API process fails.

---

### 2.2 `GET /ready`
Readiness probe. Checks database connectivity using a fast `SELECT 1` query.
- **Method**: `GET`
- **Path**: `/ready`
- **Purpose**: Readiness probe. Ensures database is reachable before routing user traffic. Returns 200 when database is healthy; returns 503 when database is stopped or unreachable.
- **Request**: None
- **Response (`200 OK`)**:
```json
{
  "status": "ready",
  "database": "connected"
}
```
*(If database is not configured in the host environment, reports `{"status": "not_configured", "database": "none"}` with 200 OK).*
- **Error Codes**:
  - `503 Service Unavailable`: Database query failed or connection refused.
  ```json
  {
    "detail": "Database unavailable: PostgreSQL connection refused at port 5432"
  }
  ```

---

### 2.3 `POST /chat`
Core inference endpoint. Sends queries to the primary model (`gemini-1.5-pro`) with retries for transient failures and automatic fallback to `gemini-1.5-flash`.
- **Method**: `POST`
- **Path**: `/chat`
- **Purpose**: Conversational analysis of budget figures with token tracking, cost attribution, and streaming support.
- **Request Body**:
```json
{
  "message": "What was the Budget Estimate for PM-KISAN in 2024-25?",
  "model": "gemini-1.5-pro",
  "stream": false
}
```
- **Response Body (`200 OK`)**:
```json
{
  "response": "The Budget Estimate (BE) for PM-KISAN in FY 2024-25 is Rs 60,000 crore under Demand No. 1...",
  "model_used": "gemini-1.5-pro",
  "tokens": {
    "prompt_tokens": 42,
    "completion_tokens": 88,
    "total_tokens": 130
  },
  "cost_usd": 0.001071,
  "latency_ms": 612.4,
  "fallback_triggered": false,
  "fallback_used": false
}
```
- **Streaming Mode (`stream: true`)**:
  Returns `text/event-stream` yielding word deltas and a final completion object containing token usage and financial cost metrics.
- **Retry & Fallback Policy**:
  - Transient errors (`429`, `500`, `502`, `503`, `504`, timeouts, connection drops) are retried with exponential backoff and jitter up to `LLM_MAX_RETRIES`.
  - If all retries fail, switches seamlessly to `LLM_FALLBACK_MODEL` (`gemini-1.5-flash`).
  - Auth and configuration errors (`400`, `401`, `403`, `404`) are NOT retried and do NOT trigger fallback.
- **Error Codes**:
  - `422 Unprocessable Entity`: Invalid request body or empty message.
  - `500 Internal Server Error`: Both primary and fallback models failed, or non-transient configuration error.

---

### 2.4 `GET /usage`
Financial and telemetry monitoring endpoint.
- **Method**: `GET`
- **Path**: `/usage`
- **Purpose**: Aggregates token consumption, financial cost (USD), model breakdowns, daily usage trends, and recent request logs.
- **Request**: None
- **Response Body (`200 OK`)**:
```json
{
  "total_requests": 28,
  "total_tokens": 14250,
  "total_prompt_tokens": 9800,
  "total_completion_tokens": 4450,
  "total_cost_usd": 0.03824,
  "model_breakdown": {
    "gemini-1.5-pro": {
      "requests": 24,
      "prompt_tokens": 8900,
      "completion_tokens": 4100,
      "total_tokens": 13000,
      "cost_usd": 0.03685
    },
    "gemini-1.5-flash": {
      "requests": 4,
      "prompt_tokens": 900,
      "completion_tokens": 350,
      "total_tokens": 1250,
      "cost_usd": 0.00139
    }
  },
  "daily_usage": [
    {
      "date": "2026-11-01",
      "requests": 28,
      "prompt_tokens": 9800,
      "completion_tokens": 4450,
      "total_tokens": 14250,
      "cost_usd": 0.03824
    }
  ],
  "recent_logs": [
    {
      "id": 28,
      "timestamp": "2026-11-01T15:00:00Z",
      "model": "gemini-1.5-pro",
      "prompt_tokens": 42,
      "completion_tokens": 88,
      "total_tokens": 130,
      "cost_usd": 0.001071,
      "latency_ms": 612.4,
      "status": "success"
    }
  ]
}
```
- **Error Codes**: `500 Internal Server Error` if query fails.

---

## 3. Database Schema

### Table: `usage_logs`
Tracks every completed and failed LLM interaction for auditability, latency profiling, and cost accounting.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique log entry identifier |
| `timestamp` | TIMESTAMP / DATETIME | NOT NULL, DEFAULT UTC_NOW | UTC timestamp when request executed |
| `model` | VARCHAR(64) | NOT NULL | Model identifier (e.g., `gemini-1.5-pro`) |
| `prompt_tokens` | INTEGER | NOT NULL, DEFAULT 0 | Input prompt token count |
| `completion_tokens` | INTEGER | NOT NULL, DEFAULT 0 | Generated output token count |
| `total_tokens` | INTEGER | NOT NULL, DEFAULT 0 | Sum of prompt and completion tokens |
| `cost_usd` | FLOAT | NOT NULL, DEFAULT 0.0 | Estimated cost based on model pricing |
| `latency_ms` | FLOAT | NOT NULL, DEFAULT 0.0 | Request roundtrip latency in milliseconds |
| `status` | VARCHAR(32) | NOT NULL | `success`, `fallback_success`, or `error` |
| `error_message` | TEXT | NULLABLE | Error message or traceback if request failed |

*Note: Database extensions include `vector` (pgvector) enabled on PostgreSQL for future vector search stages.*
