"""Computes and persists one day's composite score for an asset (Phase 7).
Reads exclusively from the local DB via MockMarketDataProvider -- never
calls FinMind directly -- so this always scores whatever the ingestion
step (MarketDataIngestionService) just wrote in the same request/session,
without spending any extra provider quota.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.analytics import scoring, technical
from app.analytics.fundamentals_growth import revenue_growth_yoy
from app.analytics.scoring_types import SubScores
from app.models.score import Score
from app.providers.market_data_provider import AssetNotFoundError
from app.providers.mock_provider import MockMarketDataProvider
from app.repositories.asset_repository import AssetRepository
from app.repositories.score_repository import ScoreRepository

TAIEX_TICKER = "TAIEX"
SOURCE = "CALCULATED"
_TWO_DP = Decimal("0.01")


def _round2(value: Decimal | None) -> Decimal | None:
    return value.quantize(_TWO_DP) if value is not None else None


class ScoringService:
    def __init__(self, db: Session):
        self.market_data = MockMarketDataProvider(db)
        self.assets = AssetRepository(db)
        self.scores_repo = ScoreRepository(db)

    def compute_and_store(self, ticker: str, on_date: date) -> Score:
        asset = self.assets.get_by_ticker(ticker)
        if asset is None:
            raise AssetNotFoundError(ticker)

        valuation = self.market_data.get_valuation(ticker, on_date=on_date)
        fundamentals = self.market_data.get_fundamentals(ticker)
        ttm = next((f for f in fundamentals if f.period == "TTM"), None)

        points = [p for p in self.market_data.get_historical_prices(ticker) if p.date <= on_date]
        points.sort(key=lambda p: p.date)
        closes = [p.close for p in points]
        highs = [p.high if p.high is not None else p.close for p in points]
        lows = [p.low if p.low is not None else p.close for p in points]
        snapshot = technical.latest_snapshot(closes, highs, lows)
        latest_close = closes[-1] if closes else None

        growth_pct = revenue_growth_yoy(fundamentals)
        growth_pct = growth_pct * 100 if growth_pct is not None else None

        regime = None
        try:
            taiex_points = [p for p in self.market_data.get_historical_prices(TAIEX_TICKER) if p.date <= on_date]
            taiex_points.sort(key=lambda p: p.date)
            regime = scoring.detect_regime([p.close for p in taiex_points])
        except AssetNotFoundError:
            # TAIEX not provisioned yet (e.g. this method called outside the
            # normal ingestion flow) -- the other three sub-scores are still
            # meaningful without a regime read; composite_score falls back
            # to the equal-weighted NEUTRAL table for regime=None.
            regime = None

        sub_scores = SubScores(
            value=scoring.value_score(valuation.pe_ratio, valuation.pb_ratio),
            growth=scoring.growth_score(growth_pct),
            momentum=scoring.momentum_score(snapshot["rsi_14"], latest_close, snapshot["sma_20"], snapshot["macd_histogram"]),
            quality=scoring.quality_score(
                ttm.roe if ttm is not None else None,
                ttm.debt_ratio if ttm is not None else None,
                valuation.dividend_yield,
            ),
        )
        result = scoring.composite_score(sub_scores, regime)

        return self.scores_repo.upsert(
            asset.id,
            on_date,
            value_score=_round2(result.sub_scores.value),
            growth_score=_round2(result.sub_scores.growth),
            momentum_score=_round2(result.sub_scores.momentum),
            quality_score=_round2(result.sub_scores.quality),
            composite_score=_round2(result.composite),
            regime=result.regime,
            missing_components=",".join(result.missing_components),
            source=SOURCE,
        )
