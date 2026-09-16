from app.analytics.signal_rules import DEFAULT_RULES


def test_versions_bootstraps_version_1_on_first_call(client):
    resp = client.get("/api/strategy/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["version_number"] == 1
    assert body[0]["status"] == "ACTIVE"
    assert body[0]["rules"] == DEFAULT_RULES.to_dict()


def test_propose_small_change_auto_applies(client):
    new_rules = {**DEFAULT_RULES.to_dict(), "rsi_period": 21}
    resp = client.post("/api/strategy/versions", json={"proposed_rules": new_rules, "reason": "Tune RSI"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["version_number"] == 2
    assert body["status"] == "ACTIVE"
    assert body["change_type"] == "AUTO_APPLIED"
    assert body["rules"]["rsi_period"] == 21

    versions = client.get("/api/strategy/versions").json()
    assert len(versions) == 2
    assert [v["status"] for v in versions] == ["ACTIVE", "SUPERSEDED"]


def test_propose_big_change_is_queued(client):
    new_rules = {**DEFAULT_RULES.to_dict(), "bollinger_touch_enabled": True}
    resp = client.post("/api/strategy/versions", json={"proposed_rules": new_rules, "reason": "Add Bollinger touch"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["proposed_rules"] == new_rules

    pending = client.get("/api/strategy/pending").json()
    assert len(pending) == 1
    assert pending[0]["status"] == "PENDING"

    # Not applied -- still version 1 active.
    versions = client.get("/api/strategy/versions").json()
    assert len(versions) == 1


def test_confirm_pending_change(client):
    new_rules = {**DEFAULT_RULES.to_dict(), "bollinger_touch_enabled": True}
    pending = client.post("/api/strategy/versions", json={"proposed_rules": new_rules, "reason": "x"}).json()

    resp = client.post(f"/api/strategy/pending/{pending['id']}/confirm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["change_type"] == "CONFIRMED"
    assert body["rules"] == new_rules


def test_reject_pending_change(client):
    new_rules = {**DEFAULT_RULES.to_dict(), "bollinger_touch_enabled": True}
    pending = client.post("/api/strategy/versions", json={"proposed_rules": new_rules, "reason": "x"}).json()

    resp = client.post(f"/api/strategy/pending/{pending['id']}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

    versions = client.get("/api/strategy/versions").json()
    assert len(versions) == 1  # never applied


def test_confirming_an_already_rejected_change_is_a_400(client):
    new_rules = {**DEFAULT_RULES.to_dict(), "bollinger_touch_enabled": True}
    pending = client.post("/api/strategy/versions", json={"proposed_rules": new_rules, "reason": "x"}).json()
    client.post(f"/api/strategy/pending/{pending['id']}/reject")

    resp = client.post(f"/api/strategy/pending/{pending['id']}/confirm")
    assert resp.status_code == 400


def test_confirming_an_unknown_pending_change_is_a_404(client):
    resp = client.post("/api/strategy/pending/999/confirm")
    assert resp.status_code == 404
