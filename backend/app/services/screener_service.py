"""PRD Sec.17: a filter, not a recommendation engine — results are always
"meets criteria", never a buy/sell verdict (see ScreenerResult's docstring).

V1 limitation: `market_cap_gt` and `dividend_yield_gt` are accepted by the
route's query params but rejected here with a clear error. Computing either
needs shares-outstanding / dividend-yield data that doesn't exist anywhere
in the Phase 1 schema — adding it wasn't part of this phase's scope, and
inventing the number would be worse than refusing the filter.
"""

from app.analytics import technical
from app.analytics.fundamentals_growth import revenue_growth_yoy
from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider
from app.repositories.asset_repository import AssetRepository
from app.repositories.score_repository import ScoreRepository
from app.schemas.screener import ScreenerResult

UNSUPPORTED_FILTERS = ("market_cap_gt", "dividend_yield_gt")


class ScreenerService:
    def __init__(self, db, market_data: MarketDataProvider):
        self.assets = AssetRepository(db)
        self.scores_repo = ScoreRepository(db)
        self.market_data = market_data

    def screen(
        self,
        revenue_growth_gt=None,
        roe_gt=None,
        pe_lt=None,
        market_cap_gt=None,
        dividend_yield_gt=None,
        foreign_net_buy_gt=None,
        rsi_lt=None,
        rsi_gt=None,
        above_sma_20=None,
        composite_score_gt=None,
    ) -> list[ScreenerResult]:
        if market_cap_gt is not None or dividend_yield_gt is not None:
            raise ValueError(
                "market_cap_gt and dividend_yield_gt are not supported in V1 "
                "(no shares-outstanding/dividend-yield data in the schema)."
            )

        results = []
        for asset in self.assets.list():
            if asset.asset_type not in ("STOCK", "ETF"):
                continue
            try:
                fundamentals = self.market_data.get_fundamentals(asset.ticker)
                quote = self.market_data.get_quote(asset.ticker)
            except AssetNotFoundError:
                continue

            ttm = next((f for f in fundamentals if f.period == "TTM"), None)
            roe_pct = (ttm.roe * 100) if ttm and ttm.roe is not None else None
            pe_ratio = (quote.price / ttm.eps) if ttm and ttm.eps not in (None, 0) else None
            growth_pct = revenue_growth_yoy(fundamentals)
            growth_pct = (growth_pct * 100) if growth_pct is not None else None

            # Only pay for institutional-flow/technical-indicator data when a
            # filter that actually needs it was requested -- otherwise every
            # screener call (even one that only passes roe_gt) would fetch
            # full price/institutional-flow history and recompute all 6
            # technical indicators for every asset for nothing.
            foreign_net_buy = None
            if foreign_net_buy_gt is not None:
                foreign_net_buy = _latest_foreign_net_buy(self.market_data, asset.ticker)

            rsi_14 = above_sma20_flag = None
            if rsi_lt is not None or rsi_gt is not None or above_sma_20 is not None:
                rsi_14, above_sma20_flag = _latest_rsi_and_sma_flag(self.market_data, asset.ticker)

            # Reads the latest *persisted* score (Phase 7) -- never
            # recomputed here, same "only pay for it if requested" guard.
            composite_score = None
            if composite_score_gt is not None:
                composite_score = _latest_composite_score(self.scores_repo, asset.id)

            if revenue_growth_gt is not None and (growth_pct is None or growth_pct <= revenue_growth_gt):
                continue
            if roe_gt is not None and (roe_pct is None or roe_pct <= roe_gt):
                continue
            if pe_lt is not None and (pe_ratio is None or pe_ratio >= pe_lt):
                continue
            if foreign_net_buy_gt is not None and (foreign_net_buy is None or foreign_net_buy <= foreign_net_buy_gt):
                continue
            if rsi_lt is not None and (rsi_14 is None or rsi_14 >= rsi_lt):
                continue
            if rsi_gt is not None and (rsi_14 is None or rsi_14 <= rsi_gt):
                continue
            if above_sma_20 is not None and (above_sma20_flag is None or above_sma20_flag != above_sma_20):
                continue
            if composite_score_gt is not None and (composite_score is None or composite_score <= composite_score_gt):
                continue

            results.append(
                ScreenerResult(
                    ticker=asset.ticker,
                    asset_name=asset.name,
                    revenue_growth_yoy=growth_pct,
                    roe=roe_pct,
                    pe_ratio=pe_ratio,
                    foreign_net_buy=foreign_net_buy,
                    rsi_14=rsi_14,
                    above_sma_20=above_sma20_flag,
                    composite_score=composite_score,
                    meets_criteria=True,
                )
            )
        return results


def _latest_composite_score(scores_repo: ScoreRepository, asset_id: int):
    rows = scores_repo.range(asset_id)
    return rows[-1].composite_score if rows else None


def _latest_foreign_net_buy(market_data: MarketDataProvider, ticker: str) -> int | None:
    try:
        flows = market_data.get_institutional_flows(ticker)
    except AssetNotFoundError:
        return None
    return flows[-1].foreign_net if flows else None


def _latest_rsi_and_sma_flag(market_data: MarketDataProvider, ticker: str):
    try:
        points = market_data.get_historical_prices(ticker)
    except AssetNotFoundError:
        return None, None
    if not points:
        return None, None

    points = sorted(points, key=lambda p: p.date)
    closes = [p.close for p in points]
    highs = [p.high if p.high is not None else p.close for p in points]
    lows = [p.low if p.low is not None else p.close for p in points]
    snapshot = technical.latest_snapshot(closes, highs, lows)

    rsi_14 = snapshot["rsi_14"]
    sma_20 = snapshot["sma_20"]
    above_sma_20 = (closes[-1] > sma_20) if sma_20 is not None else None
    return rsi_14, above_sma_20
