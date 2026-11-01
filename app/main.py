import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select, text
from sqlalchemy.orm import Session

try:
    from app.config import Settings, get_settings
    from app.database import UsageRecord, engine, get_db, init_db
    from app.llm import LLMService
    from app.schemas import (
        ChatRequest,
        ChatResponse,
        DailyUsageSummary,
        ModelUsageSummary,
        TokenUsage,
        UsageLogItem,
        UsageSummaryResponse,
    )
except ImportError:
    from config import Settings, get_settings
    from database import UsageRecord, engine, get_db, init_db
    from llm import LLMService
    from schemas import (
        ChatRequest,
        ChatResponse,
        DailyUsageSummary,
        ModelUsageSummary,
        TokenUsage,
        UsageLogItem,
        UsageSummaryResponse,
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup if database is accessible
    try:
        init_db()
    except Exception as e:
        logger.warning(f"Database initialization deferred (database not ready yet): {e}")
    yield


app = FastAPI(
    title="BudgetDiff API",
    description="Track central budget estimates, revised estimates, actuals, and diffs.",
    version="0.2.0",
    lifespan=lifespan,
)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]
llm_service = LLMService()


@app.get("/health")
def health(settings: SettingsDep) -> dict:
    """Liveness probe: fast and does not call LLM or DB."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/ready")
def ready(settings: SettingsDep) -> dict:
    """Readiness probe: verifies database connectivity with a lightweight SELECT 1 query."""
    if not settings.database_url:
        return {
            "status": "not_configured",
            "database": "none",
        }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
        }
    except Exception as e:
        logger.warning(f"Database readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {e}",
        ) from e


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Execute conversational LLM query with retry, timeout, fallback model,
    and automatic token and cost tracking.
    """
    if request.stream:
        return StreamingResponse(
            llm_service.stream_generate(request.message, model_override=request.model),
            media_type="text/event-stream",
        )

    try:
        res = await llm_service.generate(request.message, model_override=request.model)
        return ChatResponse(
            response=res["response"],
            model_used=res["model_used"],
            tokens=TokenUsage(
                prompt_tokens=res["prompt_tokens"],
                completion_tokens=res["completion_tokens"],
                total_tokens=res["total_tokens"],
            ),
            cost_usd=res["cost_usd"],
            latency_ms=res["latency_ms"],
            fallback_triggered=res["fallback_triggered"],
            fallback_used=res.get("fallback_used", res["fallback_triggered"]),
        )
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation failed: {e}",
        ) from e


@app.get("/usage", response_model=UsageSummaryResponse)
def get_usage(db: DbDep) -> UsageSummaryResponse:
    """
    Return cumulative token usage and financial cost statistics,
    including model breakdowns, daily usage, and recent request logs.
    """
    # Summary totals
    totals = db.execute(
        select(
            func.count(UsageRecord.id).label("total_requests"),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0).label("total_prompt_tokens"),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0).label("total_completion_tokens"),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0).label("total_cost_usd"),
        )
    ).one()

    # Breakdown by model
    model_stats = db.execute(
        select(
            UsageRecord.model,
            func.count(UsageRecord.id).label("requests"),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0).label("cost_usd"),
        ).group_by(UsageRecord.model)
    ).all()

    breakdown = {}
    for row in model_stats:
        breakdown[row.model] = ModelUsageSummary(
            requests=row.requests,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            total_tokens=row.total_tokens,
            cost_usd=round(row.cost_usd, 6),
        )

    # Daily usage aggregation
    daily_stats = db.execute(
        select(
            func.date(UsageRecord.timestamp).label("usage_date"),
            func.count(UsageRecord.id).label("requests"),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0).label("cost_usd"),
        )
        .group_by(func.date(UsageRecord.timestamp))
        .order_by(desc("usage_date"))
    ).all()

    daily_usage_items = [
        DailyUsageSummary(
            date=str(row.usage_date),
            requests=row.requests,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            total_tokens=row.total_tokens,
            cost_usd=round(row.cost_usd, 6),
        )
        for row in daily_stats
    ]

    # 20 most recent logs
    recent = db.execute(
        select(UsageRecord).order_by(desc(UsageRecord.id)).limit(20)
    ).scalars().all()

    log_items = [
        UsageLogItem(
            id=item.id,
            timestamp=item.timestamp.isoformat(),
            model=item.model,
            prompt_tokens=item.prompt_tokens,
            completion_tokens=item.completion_tokens,
            total_tokens=item.total_tokens,
            cost_usd=round(item.cost_usd, 6),
            latency_ms=item.latency_ms,
            status=item.status,
        )
        for item in recent
    ]

    return UsageSummaryResponse(
        total_requests=totals.total_requests,
        total_tokens=totals.total_tokens,
        total_prompt_tokens=totals.total_prompt_tokens,
        total_completion_tokens=totals.total_completion_tokens,
        total_cost_usd=round(totals.total_cost_usd, 6),
        model_breakdown=breakdown,
        daily_usage=daily_usage_items,
        recent_logs=log_items,
    )
