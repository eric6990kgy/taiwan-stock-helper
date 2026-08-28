"""PRD Sec.17: a filter, not a recommendation engine — results are always
"meets criteria", never a buy/sell verdict (see ScreenerResult's docstring).

V1 limitation: `market_cap_gt` and `dividend_yield_gt` are accepted by the
route's query params but rejected here with a clear error. Computing either
needs shares-outstanding / dividend-yield data that doesn't exist anywhere
in the Phase 1 schema — adding it wasn't part of this phase's scope, and
inventing the number would be worse than refusing the filter.
"""

from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider
from app.repositories.asset_repository import AssetRepository
from app.schemas.screener import ScreenerResult

UNSUPPORTED_FILTERS = ("market_cap_gt", "dividend_yield_gt")


def _revenue_growth_yoy(fundamentals: list) -> object:
    rows = sorted((f for f in fundamentals if f.revenue is not None), key=lambda f: f.period)
    if len(rows) < 2:
        return None
    previous, latest = rows[-2], rows[-1]
    if previous.revenue == 0:
        return None
    return (latest.revenue - previous.revenue) / previous.revenue


class ScreenerService:
    def __init__(self, db, market_data: MarketDataProvider):
        self.assets = AssetRepository(db)
        self.market_data = market_data

    def screen(
        self,
        revenue_growth_gt=None,
        roe_gt=None,
        pe_lt=None,
        market_cap_gt=None,
        dividend_yield_gt=None,
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
            growth_pct = _revenue_growth_yoy(fundamentals)
            growth_pct = (growth_pct * 100) if growth_pct is not None else None

            if revenue_growth_gt is not None and (growth_pct is None or growth_pct <= revenue_growth_gt):
                continue
            if roe_gt is not None and (roe_pct is None or roe_pct <= roe_gt):
                continue
            if pe_lt is not None and (pe_ratio is None or pe_ratio >= pe_lt):
                continue

            results.append(
                ScreenerResult(
                    ticker=asset.ticker,
                    asset_name=asset.name,
                    revenue_growth_yoy=growth_pct,
                    roe=roe_pct,
                    pe_ratio=pe_ratio,
                    meets_criteria=True,
                )
            )
        return results
