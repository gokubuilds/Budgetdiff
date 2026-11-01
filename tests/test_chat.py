from unittest.mock import patch


def test_chat_returns_structured_json(client):
    payload = {"message": "What is the budget estimate for PM-KISAN?"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "response" in data
    assert "model_used" in data
    assert "tokens" in data
    assert "prompt_tokens" in data["tokens"]
    assert "completion_tokens" in data["tokens"]
    assert "total_tokens" in data["tokens"]
    assert data["tokens"]["total_tokens"] > 0
    assert "cost_usd" in data
    assert "latency_ms" in data
    assert "fallback_triggered" in data
    assert data["fallback_triggered"] is False


def test_chat_validation_empty_message(client):
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_streaming(client):
    payload = {"message": "Explain BE vs RE", "stream": True}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "data:" in content
    assert '"done": true' in content or '"done":true' in content


@patch("app.llm.LLMService._call_gemini_api")
def test_chat_triggers_fallback_on_primary_failure(mock_call, client):
    # Make primary model fail, but fallback succeed
    async def side_effect(model, message, timeout):
        if model == "gemini-1.5-pro":
            raise RuntimeError("Primary model rate limit / timeout")
        return {
            "text": "Fallback model answer",
            "prompt_tokens": 20,
            "completion_tokens": 10,
        }

    mock_call.side_effect = side_effect

    # Set temporary settings with an API key so it attempts live call
    with patch("app.llm.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "fake_key_for_test"
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.primary_model = "gemini-1.5-pro"
        mock_settings.return_value.fallback_model = "gemini-1.5-flash"
        mock_settings.return_value.llm_timeout_seconds = 1.0
        mock_settings.return_value.llm_max_retries = 1

        response = client.post("/chat", json={"message": "Test fallback"})
        assert response.status_code == 200
        data = response.json()
        assert data["fallback_triggered"] is True
        assert data["fallback_used"] is True
        assert data["model_used"] == "gemini-1.5-flash"
        assert data["response"] == "Fallback model answer"


@patch("app.llm.LLMService._call_gemini_api")
def test_chat_does_not_fallback_on_401(mock_call, client):
    from app.llm import LLMConfigurationError

    # Simulate 401 Unauthorized
    async def side_effect(model, message, timeout):
        raise LLMConfigurationError("Non-transient Gemini API error 401: Invalid API Key")

    mock_call.side_effect = side_effect

    with patch("app.llm.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "invalid_key"
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.primary_model = "gemini-1.5-pro"
        mock_settings.return_value.fallback_model = "gemini-1.5-flash"
        mock_settings.return_value.llm_timeout_seconds = 1.0
        mock_settings.return_value.llm_max_retries = 2

        response = client.post("/chat", json={"message": "Test auth failure"})
        # Must fail with 500 error and NOT trigger fallback to hide invalid key
        assert response.status_code == 500
        # Call should have been attempted only once (no retries for 401)
        assert mock_call.call_count == 1


def test_cost_log_file_written(client):
    import json
    from pathlib import Path

    response = client.post("/chat", json={"message": "Cost logging check"})
    assert response.status_code == 200

    cost_log_path = Path("logs/cost.jsonl")
    assert cost_log_path.exists()

    with open(cost_log_path, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) > 0
    last_record = json.loads(lines[-1])
    assert "timestamp" in last_record
    assert "model" in last_record
    assert "input_tokens" in last_record
    assert "output_tokens" in last_record
    assert "latency" in last_record
    assert "cost" in last_record
    assert "fallback_used" in last_record

