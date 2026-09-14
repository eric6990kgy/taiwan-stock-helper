"""Allocation/performance/risk views, all built by re-aggregating
PortfolioService's already-computed holdings — no new financial formulas.
See schemas/analytics.py for why `performance` is a snapshot.

Phase A (個股訊號引擎規格書, confirmed 2026-09-14) added the risk
hard-constraint checks on `risk`, plus two new views: `drawdown` and
`benchmark`/alpha. Both reconstruct history from transactions + price_history
(app.analytics.history) rather than waiting on a future daily-snapshot job —
see that module's docstring."""

from datetime import date, timedelta
from decimal import Decimal

from app import config
from app.analytics import risk_limits
from app.analytics.benchmark import calculate_alpha, period_return
from app.analytics.history import build_equity_curve, evaluate_drawdown
from app.repositories.price_repository import PriceRepository
from app.schemas.analytics import (
    AllocationEntry,
    AllocationRead,
    BenchmarkComparisonRead,
    DrawdownRead,
    LimitViolationEntry,
    PerformanceRead,
    RiskRead,
    SectorConcentrationEntry,
    TopHolding,
)
from app.services.portfolio_service import PortfolioService

TOP_HOLDINGS_LIMIT = 10
DEFAULT_LOOKBACK_DAYS = 365


class AnalyticsService:
    def __init__(self, portfolio_service: PortfolioService):
        self.portfolio_service = portfolio_service
        self.prices = PriceRepository(portfolio_service.db)

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

        # The confirmed 15%/30% limits (個股訊號引擎規格書) are about
        # concentration *within the individual-stock sleeve* -- they police
        # the agent's own stock-picking activity, not the account as a
        # whole. Weighing them against total net worth would count cash and
        # the deliberate Global ETF/passive allocation as "concentration
        # risk" (an early version of this endpoint did exactly that: with
        # the demo data, it flagged the Global ETF position at 65% weight
        # as a violation, which is nonsensical -- that position is the
        # benchmark this system is supposed to beat, not something it
        # should ever flag). So: filter to asset_type == STOCK first, then
        # recompute weight as a fraction of that STOCK-only subtotal.
        stock_holdings = [h for h in holdings if self.portfolio_service.assets.get(h.asset_id).asset_type == "STOCK"]
        stock_total = sum((h.market_value for h in stock_holdings), Decimal("0"))

        position_weights = {
            h.ticker: (h.market_value / stock_total if stock_total != 0 else None) for h in stock_holdings
        }

        stock_sector_totals: dict[str | None, Decimal] = {}
        for h in stock_holdings:
            asset = self.portfolio_service.assets.get(h.asset_id)
            stock_sector_totals[asset.sector] = stock_sector_totals.get(asset.sector, Decimal("0")) + h.market_value
        sector_weights = {
            sector: (value / stock_total if stock_total != 0 else None)
            for sector, value in stock_sector_totals.items()
        }

        position_violations = risk_limits.check_limits(
            position_weights, config.RISK_POSITION_LIMIT_PCT, risk_limits.POSITION
        )
        sector_violations = risk_limits.check_limits(sector_weights, config.RISK_SECTOR_LIMIT_PCT, risk_limits.SECTOR)

        return RiskRead(
            sector_concentration=sector_concentration,
            top_holdings=top_holdings,
            max_single_position_weight=max_weight,
            position_limit_pct=config.RISK_POSITION_LIMIT_PCT,
            sector_limit_pct=config.RISK_SECTOR_LIMIT_PCT,
            position_limit_violations=[LimitViolationEntry(**v.__dict__) for v in position_violations],
            sector_limit_violations=[LimitViolationEntry(**v.__dict__) for v in sector_violations],
        )

    def _equity_curve(self, start: date, end: date):
        all_txns = self.portfolio_service.get_all_transaction_inputs()
        if not all_txns:
            return [], all_txns

        asset_ids = {t.asset_id for t in all_txns}
        # start=None: fetch each asset's full history up to `end`, not just
        # rows inside [start, end] -- a position opened before `start` still
        # needs its last pre-window close to be valued correctly on day
        # `start` itself, not excluded for lack of a price.
        price_history = {
            asset_id: [(row.date, row.close) for row in self.prices.range(asset_id, start=None, end=end)]
            for asset_id in asset_ids
        }
        return build_equity_curve(all_txns, price_history, start, end), all_txns

    def get_drawdown(self, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> DrawdownRead | None:
        """None when there's no transaction history yet -- nothing to
        evaluate, not a fabricated OK status."""
        end = date.today()
        start = end - timedelta(days=lookback_days)

        curve, _ = self._equity_curve(start, end)
        status = evaluate_drawdown(curve, config.RISK_DRAWDOWN_PAUSE_PCT, config.RISK_DRAWDOWN_STOP_PCT)
        if status is None:
            return None

        return DrawdownRead(
            as_of=status.as_of,
            equity=status.equity,
            peak_equity=status.peak_equity,
            peak_date=status.peak_date,
            drawdown_pct=status.drawdown_pct,
            action=status.action,
            pause_threshold_pct=config.RISK_DRAWDOWN_PAUSE_PCT,
            stop_threshold_pct=config.RISK_DRAWDOWN_STOP_PCT,
        )

    def get_benchmark_comparison(self, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> BenchmarkComparisonRead:
        end = date.today()
        start = end - timedelta(days=lookback_days)
        notes: list[str] = []

        curve, all_txns = self._equity_curve(start, end)
        portfolio_return = None
        if len(curve) >= 2:
            portfolio_return = period_return(curve[0].equity, curve[-1].equity)
            if portfolio_return is None and all_txns:
                notes.append(f"投資組合在{start}當時的權益為0(尚未建倉),無法計算這段期間的報酬率。")
        elif not all_txns:
            notes.append("尚無任何交易紀錄,無法計算投資組合報酬率。")

        benchmark_asset = self.portfolio_service.assets.get_by_ticker(config.BENCHMARK_TICKER)
        benchmark_return = None
        if benchmark_asset is None:
            notes.append(f"尚未新增基準標的 {config.BENCHMARK_TICKER}——請先透過 POST /api/assets 新增,再執行一次市場資料更新。")
        else:
            benchmark_rows = self.prices.range(benchmark_asset.id, start, end)
            if len(benchmark_rows) >= 2:
                benchmark_return = period_return(benchmark_rows[0].close, benchmark_rows[-1].close)
            else:
                notes.append(f"{config.BENCHMARK_TICKER} 在這段期間內的價格資料不足,請先執行一次市場資料更新。")

        alpha = calculate_alpha(portfolio_return, benchmark_return)

        return BenchmarkComparisonRead(
            start_date=start,
            end_date=end,
            portfolio_return_pct=portfolio_return,
            benchmark_ticker=config.BENCHMARK_TICKER,
            benchmark_return_pct=benchmark_return,
            alpha_pct=alpha,
            note=" ".join(notes) or None,
        )
