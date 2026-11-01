import asyncio
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

try:
    from app.config import get_settings
    from app.database import SessionLocal, UsageRecord
except ImportError:
    from config import get_settings
    from database import SessionLocal, UsageRecord

logger = logging.getLogger(__name__)

# Official pricing per 1M tokens (USD)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-1.5-pro": {
        "prompt": 3.50 / 1_000_000,
        "completion": 10.50 / 1_000_000,
    },
    "gemini-1.5-flash": {
        "prompt": 0.075 / 1_000_000,
        "completion": 0.30 / 1_000_000,
    },
}


class LLMUnavailable(Exception):
    """Raised when an LLM provider is unavailable due to transient/server errors (timeouts, 429, 5xx)."""

    pass


class LLMConfigurationError(Exception):
    """Raised for non-transient configuration/auth errors (400, 401, 403, 404)."""

    pass


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated cost in USD based on model pricing."""
    rates = MODEL_PRICING.get(
        model,
        {"prompt": 0.50 / 1_000_000, "completion": 1.50 / 1_000_000},
    )
    cost = (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])
    return round(cost, 8)


def estimate_tokens(text: str) -> int:
    """Rough token estimation (approx 4 chars per token) for fallback/mock."""
    return max(1, len(text) // 4)


def log_cost_record(
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency: float,
    cost: float,
    fallback_used: bool,
) -> None:
    """Append one cost tracking record per completed LLM call to logs/cost.jsonl."""
    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency": round(latency, 2),
            "cost": cost,
            "fallback_used": fallback_used,
        }
        with open(logs_dir / "cost.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.error(f"Failed to append to logs/cost.jsonl: {e}")


def record_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    status: str = "success",
    error_message: str | None = None,
    fallback_used: bool = False,
) -> float:
    """Persist usage statistics and estimated cost to the database and cost log file."""
    total_tokens = prompt_tokens + completion_tokens
    cost = calculate_cost(model, prompt_tokens, completion_tokens)

    try:
        with SessionLocal() as db:
            log_entry = UsageRecord(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=round(latency_ms, 2),
                status=status,
                error_message=error_message,
            )
            db.add(log_entry)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to record usage log: {e}")

    # Write cost log record for completed calls
    if status in ("success", "fallback_success"):
        log_cost_record(
            model=model,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            latency=latency_ms,
            cost=cost,
            fallback_used=fallback_used,
        )

    return cost


class BaseLLMProvider(ABC):
    """Abstract provider interface for LLM calls."""

    @abstractmethod
    async def generate(
        self,
        model: str,
        message: str,
        timeout: float,
    ) -> dict[str, Any]:
        """Generate response given a model and user prompt."""
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini REST API implementation."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self,
        model: str,
        message: str,
        timeout: float,
    ) -> dict[str, Any]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": message}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code in (400, 401, 403, 404):
                    raise LLMConfigurationError(
                        f"Non-transient Gemini API error {resp.status_code}: {resp.text}"
                    )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as e:
            raise LLMUnavailable(f"Gemini call timed out after {timeout}s") from e
        except httpx.NetworkError as e:
            raise LLMUnavailable(f"Gemini network connection failure: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 401, 403, 404):
                raise LLMConfigurationError(
                    f"Non-transient Gemini API error {e.response.status_code}: {e.response.text}"
                ) from e
            raise LLMUnavailable(
                f"Gemini server error {e.response.status_code}: {e.response.text}"
            ) from e

        text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts)

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", estimate_tokens(message))
        completion_tokens = usage.get("candidatesTokenCount", estimate_tokens(text))

        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }


class FakeLLMProvider(BaseLLMProvider):
    """Deterministic offline mock provider for local development, tests, and CI."""

    async def generate(
        self,
        model: str,
        message: str,
        timeout: float,
    ) -> dict[str, Any]:
        await asyncio.sleep(0.01)
        text = (
            f"[BudgetDiff AI - {model}]: Analyzed query '{message}'. "
            f"Budget figures verified against Expenditure Budget and Demand for Grants documents."
        )
        prompt_tokens = estimate_tokens(message) + 15
        completion_tokens = estimate_tokens(text)
        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }


class LLMService:
    def __init__(self):
        self.settings = get_settings()
        self.fake_provider = FakeLLMProvider()

    async def _call_gemini_api(
        self,
        model: str,
        message: str,
        timeout: float,
    ) -> dict[str, Any]:
        """
        Direct async call to Google Gemini generateContent REST endpoint.
        Uses GeminiProvider with configured API key.
        """
        settings = get_settings()
        provider = GeminiProvider(api_key=settings.gemini_api_key)
        return await provider.generate(model=model, message=message, timeout=timeout)

    async def _mock_response(
        self,
        model: str,
        message: str,
        is_fallback: bool = False,
    ) -> dict[str, Any]:
        """Offline deterministic mock response for local testing and CI."""
        settings = get_settings()
        model_name = model if not is_fallback else settings.fallback_model
        return await self.fake_provider.generate(model_name, message, timeout=1.0)

    async def generate(
        self,
        message: str,
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute LLM query with retry, timeout, and fallback model.
        Returns structured dictionary.
        """
        settings = get_settings()
        start_time = time.perf_counter()
        primary_model = model_override or settings.primary_model
        fallback_model = settings.fallback_model
        timeout = settings.llm_timeout_seconds
        max_retries = settings.llm_max_retries

        # If offline or no key or test/ci environment, return deterministic mock
        if not settings.gemini_api_key or settings.environment in ("test", "ci"):
            res = await self._mock_response(primary_model, message)
            latency_ms = (time.perf_counter() - start_time) * 1000
            cost = record_usage(
                model=primary_model,
                prompt_tokens=res["prompt_tokens"],
                completion_tokens=res["completion_tokens"],
                latency_ms=latency_ms,
                status="success",
                fallback_used=False,
            )
            return {
                "response": res["text"],
                "model_used": primary_model,
                "prompt_tokens": res["prompt_tokens"],
                "completion_tokens": res["completion_tokens"],
                "total_tokens": res["prompt_tokens"] + res["completion_tokens"],
                "cost_usd": cost,
                "latency_ms": round(latency_ms, 2),
                "fallback_triggered": False,
                "fallback_used": False,
            }

        # Attempt primary model with retries for transient errors only
        last_error = None
        for attempt in range(max_retries):
            try:
                res = await self._call_gemini_api(primary_model, message, timeout=timeout)
                latency_ms = (time.perf_counter() - start_time) * 1000
                cost = record_usage(
                    model=primary_model,
                    prompt_tokens=res["prompt_tokens"],
                    completion_tokens=res["completion_tokens"],
                    latency_ms=latency_ms,
                    status="success",
                    fallback_used=False,
                )
                return {
                    "response": res["text"],
                    "model_used": primary_model,
                    "prompt_tokens": res["prompt_tokens"],
                    "completion_tokens": res["completion_tokens"],
                    "total_tokens": res["prompt_tokens"] + res["completion_tokens"],
                    "cost_usd": cost,
                    "latency_ms": round(latency_ms, 2),
                    "fallback_triggered": False,
                    "fallback_used": False,
                }
            except LLMConfigurationError:
                # Do NOT retry and do NOT trigger fallback for auth/config errors (400, 401, 403, 404)
                raise
            except Exception as e:
                # Check if it was an HTTPStatusError with non-transient status
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (400, 401, 403, 404):
                    raise
                last_error = e
                logger.warning(
                    f"Primary model {primary_model} attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    backoff = (0.2 * (2**attempt)) + random.uniform(0.01, 0.05)
                    await asyncio.sleep(backoff)

        # Primary model failed due to transient/provider-unavailable error; execute Fallback model
        logger.info(f"Triggering fallback model: {fallback_model} due to: {last_error}")
        try:
            res = await self._call_gemini_api(fallback_model, message, timeout=timeout)
            latency_ms = (time.perf_counter() - start_time) * 1000
            cost = record_usage(
                model=fallback_model,
                prompt_tokens=res["prompt_tokens"],
                completion_tokens=res["completion_tokens"],
                latency_ms=latency_ms,
                status="fallback_success",
                fallback_used=True,
            )
            return {
                "response": res["text"],
                "model_used": fallback_model,
                "prompt_tokens": res["prompt_tokens"],
                "completion_tokens": res["completion_tokens"],
                "total_tokens": res["prompt_tokens"] + res["completion_tokens"],
                "cost_usd": cost,
                "latency_ms": round(latency_ms, 2),
                "fallback_triggered": True,
                "fallback_used": True,
            }
        except LLMConfigurationError:
            raise
        except Exception as fallback_error:
            latency_ms = (time.perf_counter() - start_time) * 1000
            record_usage(
                model=fallback_model,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                status="error",
                error_message=str(fallback_error),
                fallback_used=True,
            )
            raise RuntimeError(
                f"Both primary model ({primary_model}) and fallback ({fallback_model}) failed: "
                f"{fallback_error}"
            ) from fallback_error

    async def stream_generate(
        self,
        message: str,
        model_override: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chunks from LLM generation as Server-Sent Events (SSE)."""
        result = await self.generate(message, model_override=model_override)
        words = result["response"].split(" ")

        for i, word in enumerate(words):
            chunk = {"delta": word + (" " if i < len(words) - 1 else ""), "done": False}
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.01)

        final_chunk = {
            "done": True,
            "model_used": result["model_used"],
            "tokens": {
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "total_tokens": result["total_tokens"],
            },
            "cost_usd": result["cost_usd"],
            "latency_ms": result["latency_ms"],
            "fallback_triggered": result["fallback_triggered"],
            "fallback_used": result.get("fallback_used", result["fallback_triggered"]),
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
