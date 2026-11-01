from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or query.")
    model: str | None = Field(default=None, description="Optional model override.")
    stream: bool = Field(default=False, description="Whether to stream response chunks.")


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)


class ChatResponse(BaseModel):
    response: str
    model_used: str
    tokens: TokenUsage
    cost_usd: float
    latency_ms: float
    fallback_triggered: bool = False
    fallback_used: bool = False


class UsageLogItem(BaseModel):
    id: int
    timestamp: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    status: str


class ModelUsageSummary(BaseModel):
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class DailyUsageSummary(BaseModel):
    date: str
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class UsageSummaryResponse(BaseModel):
    total_requests: int = 0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0
    model_breakdown: dict[str, ModelUsageSummary] = Field(default_factory=dict)
    daily_usage: list[DailyUsageSummary] = Field(default_factory=list)
    recent_logs: list[UsageLogItem] = Field(default_factory=list)

