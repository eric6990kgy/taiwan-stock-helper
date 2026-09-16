"""LineNotifier tests -- all HTTP calls mocked with httpx.MockTransport, no
real network access, same pattern as test_finmind_normalization.py."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

import httpx
import pytest

from app.services.line_notifier import LineNotifier, LineNotifyError, format_recommendation_alert


def make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_disabled_when_no_token_is_a_silent_noop():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200)

    notifier = LineNotifier(client=make_client(handler), token=None)
    assert notifier.enabled is False
    notifier.broadcast("should never be sent")
    assert calls == []


def test_broadcasts_the_right_payload_when_enabled():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = request.content
        return httpx.Response(200)

    notifier = LineNotifier(client=make_client(handler), token="test-token")
    notifier.broadcast("hello")

    assert captured["url"] == "https://api.line.me/v2/bot/message/broadcast"
    assert captured["auth"] == "Bearer test-token"
    assert b'"text": "hello"' in captured["body"] or b'"text":"hello"' in captured["body"]


def test_failed_call_raises_line_notify_error_not_a_crash():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid token")

    notifier = LineNotifier(client=make_client(handler), token="bad-token")
    with pytest.raises(LineNotifyError):
        notifier.broadcast("hello")


def test_network_failure_raises_line_notify_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    notifier = LineNotifier(client=make_client(handler), token="test-token")
    with pytest.raises(LineNotifyError):
        notifier.broadcast("hello")


# ---- format_recommendation_alert -------------------------------------------


@dataclass
class FakeRecommendation:
    action: str
    previous_status: str | None
    new_status: str
    triggered_signals: list = field(default_factory=list)
    risk_blocked: bool = False
    risk_block_reason: str | None = None
    created_at: datetime = datetime(2026, 9, 14, 18, 0, 0)


def test_format_recommendation_alert_includes_ticker_and_action_label():
    rec = FakeRecommendation(action="CONSIDER_INCREASE", previous_status="NEUTRAL", new_status="BULLISH")
    message = format_recommendation_alert("2330", "台積電", rec, None, None)
    assert "2330 台積電" in message
    assert "考慮增加關注度" in message
    assert "NEUTRAL → BULLISH" in message


def test_format_recommendation_alert_lists_triggered_signals():
    rec = FakeRecommendation(
        action="CONSIDER_DECREASE",
        previous_status="NEUTRAL",
        new_status="BEARISH",
        triggered_signals=[
            {"id": "REVENUE_GROWTH_POSITIVE", "status": "BEARISH", "explanation": "營收年增率為負"},
        ],
    )
    message = format_recommendation_alert("2330", "台積電", rec, None, None)
    assert "REVENUE_GROWTH_POSITIVE BEARISH -- 營收年增率為負" in message


def test_format_recommendation_alert_includes_composite_score_and_regime():
    rec = FakeRecommendation(action="WATCH", previous_status="BULLISH", new_status="NEUTRAL")
    message = format_recommendation_alert("2330", "台積電", rec, Decimal("68.2"), "BULL")
    assert "綜合分數 68.2/100" in message
    assert "大盤 BULL" in message


def test_format_recommendation_alert_flags_risk_blocked_recommendations():
    rec = FakeRecommendation(
        action="CONSIDER_INCREASE",
        previous_status="NEUTRAL",
        new_status="BULLISH",
        risk_blocked=True,
        risk_block_reason="2330 目前部位權重 16.0%，已達或超過個股上限 15.0%。",
    )
    message = format_recommendation_alert("2330", "台積電", rec, None, None)
    assert "⚠️ 風控攔截" in message
    assert "16.0%" in message


def test_format_recommendation_alert_omits_risk_line_when_not_blocked():
    rec = FakeRecommendation(action="CONSIDER_DECREASE", previous_status="BULLISH", new_status="BEARISH")
    message = format_recommendation_alert("2330", "台積電", rec, None, None)
    assert "⚠️" not in message
