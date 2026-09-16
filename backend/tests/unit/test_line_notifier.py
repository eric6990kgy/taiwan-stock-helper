"""LineNotifier tests -- all HTTP calls mocked with httpx.MockTransport, no
real network access, same pattern as test_finmind_normalization.py."""

from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.analytics.signal_types import Signal
from app.services.line_notifier import LineNotifier, LineNotifyError, format_signal_alert


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


# ---- format_signal_alert ----------------------------------------------------


def _sig(id_, status, explanation="因為"):
    return Signal(id=id_, category="TECHNICAL", name=id_, status=status, value=None, threshold=None, as_of=date(2026, 9, 14), explanation=explanation, source="CALCULATED")


def test_format_signal_alert_none_when_everything_neutral_or_unavailable():
    sigs = [_sig("PRICE_ABOVE_SMA20", "NEUTRAL"), _sig("RSI_BULLISH", "UNAVAILABLE")]
    assert format_signal_alert("2330", "台積電", date(2026, 9, 14), sigs, None, None) is None


def test_format_signal_alert_lists_only_non_neutral_signals():
    sigs = [
        _sig("PRICE_ABOVE_SMA20", "BULLISH", "股價站上20日均線"),
        _sig("REVENUE_GROWTH_POSITIVE", "BEARISH", "營收年增率為負"),
        _sig("RSI_BULLISH", "NEUTRAL"),
        _sig("COMPOSITE_SCORE", "BULLISH", "綜合評分達標"),
    ]
    message = format_signal_alert("2330", "台積電", date(2026, 9, 14), sigs, Decimal("68.2"), "BULL")

    assert "2330 台積電" in message
    assert "PRICE_ABOVE_SMA20 BULLISH -- 股價站上20日均線" in message
    assert "REVENUE_GROWTH_POSITIVE BEARISH -- 營收年增率為負" in message
    assert "RSI_BULLISH" not in message
    assert "綜合分數 68.2/100 (BULLISH)" in message
    assert "大盤 BULL" in message
