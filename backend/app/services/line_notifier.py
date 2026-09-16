"""LINE alerts for the deterministic signal engine (added per user request,
decisions confirmed 2026-09-14). Execution stays 100% manual: this only
sends a LINE message when one of an asset's signals is BULLISH/BEARISH --
the user decides whether to act and places the order themselves. Nothing
here calls, or will ever call, a broker API.

LINE Notify (the obvious choice) shut down 2025-03-31. Using the LINE
Messaging API's `broadcast` endpoint instead -- for a personal single-user
bot, "everyone who added the bot" is just the user, and broadcast avoids
needing a public webhook to capture a specific user ID (as a `push` call
would require).

Best-effort by design, same convention as every other best-effort ingestion
step in market_data_service.py: no token configured -> silently disabled,
not an error (most dev/test environments won't have LINE set up at all); a
failed HTTP call is caught by the caller and surfaces as a
validation_warnings entry, never blocks or fails the ingestion batch.
"""

import httpx

from app.config import LINE_CHANNEL_ACCESS_TOKEN

BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"


class LineNotifyError(Exception):
    """The LINE Messaging API rejected the broadcast (bad/expired token,
    quota exceeded, malformed payload, ...). Distinct from ProviderError
    (app.providers) since this isn't a MarketDataProvider concern."""


class LineNotifier:
    def __init__(self, client: httpx.Client | None = None, token: str | None = None):
        self._client = client or httpx.Client(timeout=10.0)
        self._owns_client = client is None
        self._token = LINE_CHANNEL_ACCESS_TOKEN if token is None else token

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @property
    def enabled(self) -> bool:
        return bool(self._token)

    def broadcast(self, text: str) -> None:
        """No-op when disabled (no token configured). Raises LineNotifyError
        on any HTTP-level or API-level failure -- callers are expected to
        catch this and record it as a best-effort warning, same pattern as
        a provider call in market_data_service.py."""
        if not self.enabled:
            return

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        payload = {"messages": [{"type": "text", "text": text}]}

        try:
            response = self._client.post(BROADCAST_URL, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise LineNotifyError(f"LINE broadcast request failed: {exc}") from exc

        if response.status_code != 200:
            raise LineNotifyError(f"LINE broadcast failed with HTTP {response.status_code}: {response.text}")


# Chinese labels for the LINE message body -- kept separate from
# Signal.name/Recommendation.action (English-facing, shown in the API/UI)
# so the two surfaces can evolve independently.
_SIGNAL_EMOJI = {"BULLISH": "🟢", "BEARISH": "🔴"}
_ACTION_LABELS = {"CONSIDER_INCREASE": "考慮增加關注度", "CONSIDER_DECREASE": "考慮減碼", "WATCH": "關注"}


def format_recommendation_alert(
    ticker: str,
    asset_name: str,
    recommendation,
    composite_score,
    regime: str | None,
) -> str:
    """Builds the one-message-per-Recommendation LINE text (Phase 8) --
    only called for a Recommendation that was actually just created (the
    "only on change" upgrade over Phase 7's "fires every run"), so this
    never returns None the way format_signal_alert did. A risk-blocked
    recommendation gets an explicit ⚠️ line -- must never look like an
    ordinary one at a glance (個股訊號引擎規格書 Phase B Sec.05 P0)."""
    action_label = _ACTION_LABELS[recommendation.action]
    transition = f"{recommendation.previous_status} → {recommendation.new_status}"
    lines = [
        f"📊 {ticker} {asset_name} 每日訊號 ({recommendation.created_at.date()})",
        f"建議動作：{action_label}（{transition}）",
    ]
    for s in recommendation.triggered_signals:
        emoji = _SIGNAL_EMOJI.get(s["status"], "")
        lines.append(f"{emoji} {s['id']} {s['status']} -- {s['explanation']}")

    if composite_score is not None:
        regime_part = f"　大盤 {regime}" if regime else ""
        lines.append(f"綜合分數 {composite_score:.1f}/100{regime_part}")

    if recommendation.risk_blocked:
        lines.append(f"⚠️ 風控攔截：{recommendation.risk_block_reason}")

    return "\n".join(lines)
