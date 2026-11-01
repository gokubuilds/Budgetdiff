def test_usage_returns_summary(client):
    # Trigger a chat to record usage
    client.post("/chat", json={"message": "What is MGNREGS allocation?"})

    response = client.get("/usage")
    assert response.status_code == 200

    data = response.json()
    assert "total_requests" in data
    assert data["total_requests"] >= 1
    assert "total_tokens" in data
    assert data["total_tokens"] > 0
    assert "total_prompt_tokens" in data
    assert "total_completion_tokens" in data
    assert "total_cost_usd" in data
    assert "model_breakdown" in data
    assert len(data["model_breakdown"]) > 0
    assert "recent_logs" in data
    assert len(data["recent_logs"]) > 0
    assert "daily_usage" in data
    assert len(data["daily_usage"]) > 0

    daily = data["daily_usage"][0]
    assert "date" in daily
    assert "requests" in daily
    assert "total_tokens" in daily
    assert "cost_usd" in daily

    log = data["recent_logs"][0]
    assert "id" in log
    assert "timestamp" in log
    assert "model" in log
    assert "total_tokens" in log
    assert "cost_usd" in log

