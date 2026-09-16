"""Computes a ticker's full set of deterministic signals on demand (Phase 7
Part 2) -- unlike scores (Phase 7 Part 1), signals are never persisted (see
plan Sec.10): they're cheap to recompute from data already in the DB, so
each request just reads price/institutional-flow/fundamentals history plus
the latest persisted Score and runs the pure functions in
app.analytics.signals. Reads exclusively from the local DB via
MockMarketDataProvider -- never calls FinMind directly, same rule as
ResearchService/ScoringService.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.analytics import signals as signal_fns
from app.analytics.signal_rules import DEFAULT_RULES, SignalRules
from app.analytics.signal_types import Signal, SignalResult
from app.providers.market_data_provider import AssetNotFoundError
from app.providers.mock_provider import MockMarketDataProvider
from app.repositories.asset_repository import AssetRepository
from app.repositories.score_repository import ScoreRepository
from app.services.exceptions import NotFoundError


class SignalService:
    def __init__(self, db: Session):
        self.market_data = MockMarketDataProvider(db)
        self.assets = AssetRepository(db)
        self.scores_repo = ScoreRepository(db)

    def get_signals(self, ticker: str, as_of: date | None = None, rules: SignalRules = DEFAULT_RULES) -> SignalResult:
        asset = self.assets.get_by_ticker(ticker)
        if asset is None:
            raise NotFoundError(f"Unknown ticker: {ticker!r}")

        try:
            price_points = self.market_data.get_historical_prices(ticker)
        except AssetNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        # Even a ticker with no price history yet (freshly added, never
        # ingested) gets a full SignalResult -- every signal function
        # already reports UNAVAILABLE on empty input, so nothing here needs
        # a separate "no data at all" branch. `date.today()` is only a
        # label in that edge case (there's no real "as of" date to use).
        effective_as_of = as_of
        if effective_as_of is None:
            effective_as_of = max((p.date for p in price_points), default=date.today())

        signal_list: list[Signal] = [
            signal_fns.price_above_sma_signal(price_points, rules.sma_short, effective_as_of),
            signal_fns.price_above_sma_signal(price_points, rules.sma_long, effective_as_of),
            signal_fns.rsi_bullish_signal(price_points, effective_as_of, rules.rsi_period),
            signal_fns.macd_bullish_signal(price_points, effective_as_of),
        ]

        flows = self.market_data.get_institutional_flows(ticker, end=effective_as_of)
        signal_list.append(signal_fns.foreign_net_buying_signal(flows, effective_as_of, rules.institutional_window))
        signal_list.append(
            signal_fns.investment_trust_net_buying_signal(flows, effective_as_of, rules.institutional_window)
        )

        fundamentals = self.market_data.get_fundamentals(ticker)
        signal_list.append(signal_fns.revenue_growth_positive_signal(fundamentals, effective_as_of))
        signal_list.append(signal_fns.revenue_growth_accelerating_signal(fundamentals, effective_as_of))

        score_row = self._latest_score(asset.id, effective_as_of)
        composite_score = score_row.composite_score if score_row is not None else None
        regime = score_row.regime if score_row is not None else None
        signal_list.append(
            signal_fns.composite_score_signal(
                composite_score, effective_as_of, rules.composite_bullish, rules.composite_bearish
            )
        )

        return SignalResult(
            ticker=ticker,
            as_of=effective_as_of,
            signals=signal_list,
            overall_status=signal_fns.overall_status(signal_list),
            composite_score=composite_score,
            regime=regime,
        )

    def _latest_score(self, asset_id: int, as_of: date | None):
        """Reads the already-persisted score for `as_of` -- never
        recomputes it (spec Sec.18). Exact-date match when `as_of` is
        given; otherwise the most recent row on or before it."""
        rows = self.scores_repo.range(asset_id, end=as_of)
        return rows[-1] if rows else None
