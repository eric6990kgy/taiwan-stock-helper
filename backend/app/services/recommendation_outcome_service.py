"""Scores past Recommendations against what actually happened (Phase 10) --
the ground-truth labels the review/複盤 page, and eventually an AI report
or an ML confidence-calibration model, all need. Reuses Phase 8's
look-ahead-safe walk-forward methodology (app.analytics.signal_backtest)
against a single event instead of an aggregate backtest run.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.analytics.signal_backtest import DEFAULT_DEADZONE_PCT, DEFAULT_HORIZON, score_signal_outcome
from app.models.recommendation import Recommendation
from app.models.recommendation_outcome import RecommendationOutcome
from app.repositories.price_repository import PriceRepository
from app.repositories.recommendation_outcome_repository import RecommendationOutcomeRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.review import RecommendationOutcomeRead, ReviewSummaryRead


@dataclass(frozen=True)
class ReviewSummary:
    hits: int
    n: int

    @property
    def hit_rate(self) -> Decimal | None:
        """None (never a fabricated percentage) when there's no scored
        sample yet -- same convention as BacktestResult.hit_rate."""
        return None if self.n == 0 else Decimal(self.hits) / Decimal(self.n)


class RecommendationOutcomeService:
    def __init__(self, db: Session, horizon: int = DEFAULT_HORIZON, deadzone_pct: Decimal = DEFAULT_DEADZONE_PCT):
        self.db = db
        self.horizon = horizon
        self.deadzone_pct = deadzone_pct
        self.recommendations = RecommendationRepository(db)
        self.outcomes = RecommendationOutcomeRepository(db)
        self.prices = PriceRepository(db)

    def _resolve_as_of_date(self, recommendation: Recommendation) -> date:
        if recommendation.as_of_date is not None:
            return recommendation.as_of_date
        # Legacy row from before as_of_date existed -- fall back to the
        # nearest price_history date at-or-before whenever the scan ran,
        # same "last known value on or before that day" convention
        # app.analytics.history uses for the drawdown equity curve.
        fallback = self.prices.range(recommendation.asset_id, end=recommendation.created_at.date())
        return fallback[-1].date if fallback else recommendation.created_at.date()

    def score_due_outcomes(self) -> list[RecommendationOutcome]:
        """Retroactive batch job (same "reconstruct from what's already in
        the DB, no snapshot job required" principle as history.py's
        equity curve) -- run on every "Update Market Data" cycle, so it
        catches up on every past recommendation that's now old enough to
        score, not just future ones."""
        scored: list[RecommendationOutcome] = []
        for recommendation in self.recommendations.list_unscored():
            as_of = self._resolve_as_of_date(recommendation)
            points = self.prices.range(recommendation.asset_id, start=as_of)
            if len(points) <= self.horizon:
                continue  # not enough future price history yet -- retry on a later run
            outcome = score_signal_outcome(
                recommendation.new_status, points[0].close, points[self.horizon].close, self.deadzone_pct
            )
            row = self.outcomes.create(
                recommendation_id=recommendation.id,
                horizon_trading_days=self.horizon,
                as_of_date=points[0].date,
                outcome_date=points[self.horizon].date,
                from_close=points[0].close,
                to_close=points[self.horizon].close,
                actual_direction=outcome.actual,
                hit=outcome.hit,
            )
            scored.append(row)
        self.db.commit()
        return scored

    def get_review_summary(self, action: str | None = None) -> ReviewSummary:
        rows = self.outcomes.list(action=action)
        return ReviewSummary(hits=sum(1 for r in rows if r.hit), n=len(rows))

    def get_review_summary_read(self, action: str | None = None) -> ReviewSummaryRead:
        summary = self.get_review_summary(action=action)
        return ReviewSummaryRead(
            hits=summary.hits, n=summary.n, hit_rate=str(summary.hit_rate) if summary.hit_rate is not None else None
        )

    def list_outcomes_read(self, action: str | None = None) -> list[RecommendationOutcomeRead]:
        """Newest-scored first, joined with the parent Recommendation's
        ticker/action/risk_blocked for drill-down."""
        reads = []
        for row in self.outcomes.list(action=action):
            rec = row.recommendation
            reads.append(
                RecommendationOutcomeRead(
                    id=row.id,
                    recommendation_id=row.recommendation_id,
                    ticker=rec.asset.ticker,
                    asset_name=rec.asset.name,
                    action=rec.action,
                    call=rec.new_status,
                    actual_direction=row.actual_direction,
                    hit=row.hit,
                    horizon_trading_days=row.horizon_trading_days,
                    as_of_date=row.as_of_date,
                    outcome_date=row.outcome_date,
                    from_close=str(row.from_close),
                    to_close=str(row.to_close),
                    risk_blocked=rec.risk_blocked,
                    computed_at=row.computed_at,
                )
            )
        return reads
