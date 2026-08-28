"""Allocation/performance/risk views, all built by re-aggregating
PortfolioService's already-computed holdings — no new financial formulas.
See schemas/analytics.py for why `performance` is a snapshot and `risk`
only covers sector concentration + top holdings (volatility/drawdown are
explicitly future roadmap, PRD Sec.8.4)."""

from decimal import Decimal

from app.schemas.analytics import (
    AllocationEntry,
    AllocationRead,
    PerformanceRead,
    RiskRead,
    SectorConcentrationEntry,
    TopHolding,
)
from app.services.portfolio_service import PortfolioService

TOP_HOLDINGS_LIMIT = 10


class AnalyticsService:
    def __init__(self, portfolio_service: PortfolioService):
        self.portfolio_service = portfolio_service

    def get_allocation(self) -> AllocationRead:
        holdings = self.portfolio_service.get_holdings()
        total = sum((h.market_value for h in holdings), Decimal("0"))
        entries = [
            AllocationEntry(
                account_id=h.account_id,
                asset_id=h.asset_id,
                ticker=h.ticker,
                asset_name=h.asset_name,
                market_value=h.market_value,
                weight=h.weight,
            )
            for h in holdings
        ]
        return AllocationRead(total_market_value=total, entries=entries)

    def get_performance(self) -> PerformanceRead:
        summary = self.portfolio_service.get_summary()
        return PerformanceRead(
            total_market_value=summary.total_market_value,
            remaining_cost_basis=summary.remaining_cost_basis,
            realized_pnl=summary.realized_pnl,
            unrealized_pnl=summary.unrealized_pnl,
            total_pnl=summary.total_pnl,
            total_return_pct=summary.total_return_pct,
        )

    def get_risk(self) -> RiskRead:
        holdings = self.portfolio_service.get_holdings()

        by_sector: dict[str | None, Decimal] = {}
        for h in holdings:
            asset = self.portfolio_service.assets.get(h.asset_id)
            by_sector[asset.sector] = by_sector.get(asset.sector, Decimal("0")) + h.market_value

        total = sum(by_sector.values(), Decimal("0"))
        sector_concentration = [
            SectorConcentrationEntry(
                sector=sector,
                market_value=value,
                weight=(value / total) if total != 0 else None,
            )
            for sector, value in sorted(by_sector.items(), key=lambda kv: kv[1], reverse=True)
        ]

        top_holdings = [
            TopHolding(ticker=h.ticker, asset_name=h.asset_name, market_value=h.market_value, weight=h.weight)
            for h in sorted(holdings, key=lambda h: h.market_value, reverse=True)[:TOP_HOLDINGS_LIMIT]
        ]

        weights = [h.weight for h in holdings if h.weight is not None]
        max_weight = max(weights) if weights else None

        return RiskRead(
            sector_concentration=sector_concentration,
            top_holdings=top_holdings,
            max_single_position_weight=max_weight,
        )
