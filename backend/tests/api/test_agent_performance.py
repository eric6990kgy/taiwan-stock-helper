def test_agent_performance_summary_is_null_hit_rate_before_anything_is_scored(client):
    resp = client.get("/api/agent-performance/summary")
    assert resp.status_code == 200
    assert resp.json() == {"hits": 0, "n": 0, "hit_rate": None}


def test_agent_performance_summary_accepts_a_role_filter(client):
    resp = client.get("/api/agent-performance/summary?role=FUNDAMENTAL_ANALYST")
    assert resp.status_code == 200
    assert resp.json() == {"hits": 0, "n": 0, "hit_rate": None}
