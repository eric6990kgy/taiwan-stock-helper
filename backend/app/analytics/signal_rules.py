"""The tunable numeric parameters behind app.analytics.signals (Phase 8).
Extracted into one flat, JSON-serializable dict so a StrategyVersion can
version and diff them -- same keys with different values is a "small"
change (auto-applied), a different key set is a "big" one (queued for
confirmation), see StrategyService.

DEFAULT_RULES matches the literals Phase 7 shipped with, so every existing
caller that doesn't pass `rules` explicitly keeps behaving exactly as
before -- this module only extracts parameters that were already hardcoded
into named, versionable values.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SignalRules:
    sma_short: int = 20
    sma_long: int = 60
    rsi_period: int = 14
    institutional_window: int = 5
    composite_bullish: Decimal = Decimal(60)
    composite_bearish: Decimal = Decimal(40)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["composite_bullish"] = str(d["composite_bullish"])
        d["composite_bearish"] = str(d["composite_bearish"])
        return d

    @staticmethod
    def from_dict(d: dict) -> "SignalRules":
        """Missing keys fall back to DEFAULT_RULES rather than raising --
        a "big" strategy change (StrategyService) may store a rules dict
        with a different key set than today's fixed 6 parameters (e.g. a
        future toggle-a-signal-off change), and this signal engine has no
        notion of a partially-specified rule set yet. Tolerant merging
        here keeps that forward-compatible without over-building support
        this phase doesn't need."""
        merged = {**DEFAULT_RULES.to_dict(), **d}
        return SignalRules(
            sma_short=int(merged["sma_short"]),
            sma_long=int(merged["sma_long"]),
            rsi_period=int(merged["rsi_period"]),
            institutional_window=int(merged["institutional_window"]),
            composite_bullish=Decimal(str(merged["composite_bullish"])),
            composite_bearish=Decimal(str(merged["composite_bearish"])),
        )


DEFAULT_RULES = SignalRules()
