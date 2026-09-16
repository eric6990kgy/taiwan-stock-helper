"""Daily scan + risk-gated recommendation generation (Phase 8, 個股訊號引擎規格書
Phase B). For every watchlist asset: compute today's signals with the
active strategy version's rules, diff the overall status against the last
scan (SignalSnapshot), and -- only for tickers whose status actually
changed -- classify an action and check it against Phase A's risk/drawdown
gate *before* persisting a Recommendation. Never a BUY/SELL instruction;
never a silently-skipped risk check (spec Sec.02 目標2/3).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.analytics.signal_types import BEARISH, BULLISH, UNAVAILABLE
from app.models.recommendation import Recommendation
from app.providers.mock_provider import MockMarketDataProvider
from app.repositories.asset_repository import AssetRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.signal_snapshot_repository import SignalSnapshotRepository
from app.repositories.watchlist_repository import WatchlistRepository
from app.schemas.recommendation import RecommendationRead, TriggeredSignalRead
from app.services.analytics_service import AnalyticsService
from app.services.portfolio_service import PortfolioService
from app.services.signal_service import SignalService
from app.services.strategy_service import StrategyService

EXCLUDED_WATCHLIST_STATUSES = ("REJECTED",)

ACTION_BY_STATUS = {
    BULLISH: "CONSIDER_INCREASE",
    BEARISH: "CONSIDER_DECREASE",
    "NEUTRAL": "WATCH",
}


@dataclass
class ScanOutcome:
    """Everything needed to both persist a Recommendation and compose a
    LINE alert for it, without the caller (market_data_service) needing to
    re-derive ticker/asset name or re-run the signal computation."""

    recommendation: Recommendation
    ticker: str
    asset_name: str
    composite_score: Decimal | None
    regime: str | None


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.assets = AssetRepository(db)
        self.watchlist = WatchlistRepository(db)
        self.snapshots = SignalSnapshotRepository(db)
        self.signal_service = SignalService(db)
        self.strategy_service = StrategyService(db)
        self.recommendations_repo = RecommendationRepository(db)
        market_data = MockMarketDataProvider(db)
        self.analytics_service = AnalyticsService(PortfolioService(db, market_data))

    def list_recommendations(self, since: datetime | None = None) -> list[RecommendationRead]:
        rows = self.recommendations_repo.list(since=since)
        reads: list[RecommendationRead] = []
        for row in rows:
            asset = self.assets.get(row.asset_id)
            reads.append(
                RecommendationRead(
                    id=row.id,
                    ticker=asset.ticker if asset is not None else "?",
                    asset_name=asset.name if asset is not None else "?",
                    action=row.action,
                    previous_status=row.previous_status,
                    new_status=row.new_status,
                    triggered_signals=[TriggeredSignalRead(**s) for s in row.triggered_signals],
                    risk_blocked=row.risk_blocked,
                    risk_block_reason=row.risk_block_reason,
                    composite_score=str(row.composite_score) if row.composite_score is not None else None,
                    regime=row.regime,
                    strategy_version_id=row.strategy_version_id,
                    created_at=row.created_at,
                )
            )
        return reads

    def run_daily_scan(self) -> list[ScanOutcome]:
        active_version = self.strategy_service.get_active_version()
        rules = self.strategy_service.get_active_rules()

        outcomes: list[ScanOutcome] = []
        for entry in self.watchlist.list():
            if entry.status in EXCLUDED_WATCHLIST_STATUSES:
                continue
            asset = self.assets.get(entry.asset_id)
            if asset is None:
                continue

            result = self.signal_service.get_signals(asset.ticker, rules=rules)
            new_status = result.overall_status
            snapshot = self.snapshots.get_by_asset(asset.id)
            previous_status = snapshot.overall_status if snapshot is not None else None
            self.snapshots.upsert(asset.id, new_status)

            # Nothing to report: no prior baseline yet, no change since
            # last scan, or either side of the transition is UNAVAILABLE
            # (a data gap, not information about the stock -- never
            # information-bearing enough for a recommendation).
            if (
                previous_status is None
                or previous_status == new_status
                or new_status == UNAVAILABLE
                or previous_status == UNAVAILABLE
            ):
                continue

            action = ACTION_BY_STATUS[new_status]
            triggered = [
                {
                    "id": s.id,
                    "category": s.category,
                    "name": s.name,
                    "status": s.status,
                    "explanation": s.explanation,
                }
                for s in result.signals
                if s.status in (BULLISH, BEARISH)
            ]

            risk_blocked = False
            risk_block_reason = None
            if action == "CONSIDER_INCREASE":
                risk_blocked, risk_block_reason = self._check_risk_gate(asset.ticker)

            recommendation = Recommendation(
                asset_id=asset.id,
                strategy_version_id=active_version.id,
                action=action,
                previous_status=previous_status,
                new_status=new_status,
                triggered_signals=triggered,
                risk_blocked=risk_blocked,
                risk_block_reason=risk_block_reason,
                composite_score=result.composite_score,
                regime=result.regime,
            )
            self.db.add(recommendation)
            self.db.flush()

            outcomes.append(
                ScanOutcome(
                    recommendation=recommendation,
                    ticker=asset.ticker,
                    asset_name=asset.name,
                    composite_score=result.composite_score,
                    regime=result.regime,
                )
            )

        self.db.commit()
        return outcomes

    def _check_risk_gate(self, ticker: str) -> tuple[bool, str | None]:
        """Uses TODAY's actual position/sector weight (from the existing
        /api/analytics/risk), not a hypothetical post-trade weight --
        these recommendations carry no order size to project a future
        weight from, and this codebase never fabricates a number it
        doesn't have. A CONSIDER_INCREASE on a ticker/sector already at or
        over its limit is blocked outright; a drawdown PAUSE/STOP blocks
        every CONSIDER_INCREASE regardless of position size."""
        drawdown = self.analytics_service.get_drawdown()
        if drawdown is not None and drawdown.action in ("PAUSE_NEW_POSITIONS", "HARD_STOP"):
            return True, (
                f"目前回撤 {drawdown.drawdown_pct * 100:.1f}%，風控狀態為 {drawdown.action}，暫緩任何新增部位建議。"
            )

        risk = self.analytics_service.get_risk()
        for violation in risk.position_limit_violations:
            if violation.label == ticker:
                return True, (
                    f"{ticker} 目前部位權重 {violation.weight * 100:.1f}%，"
                    f"已達或超過個股上限 {violation.limit * 100:.1f}%。"
                )

        asset = self.assets.get_by_ticker(ticker)
        sector = asset.sector if asset is not None else None
        if sector is not None:
            for violation in risk.sector_limit_violations:
                if violation.label == sector:
                    return True, (
                        f"{sector} 產業目前權重 {violation.weight * 100:.1f}%，"
                        f"已達或超過產業上限 {violation.limit * 100:.1f}%。"
                    )

        return False, None
