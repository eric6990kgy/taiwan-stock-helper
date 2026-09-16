"""Strategy versioning (Phase 8, 個股訊號引擎規格書 Phase B Sec.05 "策略版本模型").
A strategy version is the signal engine's tunable parameter set
(app.analytics.signal_rules.SignalRules), stored as a plain dict so it can
outlive the current fixed 6-parameter shape. Exactly one version is
ACTIVE at a time; SignalService/RecommendationService always read the
active version's rules, never a hardcoded literal.

Governance (confirmed 個股訊號引擎規格書 07, applied concretely here): a
proposed change that keeps the same parameter *keys* as the active
version (only values differ) is "small" and auto-applies immediately,
logged as a new version. A change that adds/removes a key is "big" and
goes into the pending-confirmation queue instead -- never silently
promoted, never auto-expiring.
"""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.orm import Session

from app.analytics.signal_backtest import BacktestResult, walk_forward_hit_rate
from app.analytics.signal_rules import DEFAULT_RULES, SignalRules
from app.models.pending_strategy_change import PendingStrategyChange
from app.models.strategy_version import StrategyVersion
from app.repositories.pending_strategy_change_repository import PendingStrategyChangeRepository
from app.repositories.strategy_version_repository import StrategyVersionRepository
from app.schemas.strategy import PendingStrategyChangeRead, StrategyVersionRead
from app.services.exceptions import NotFoundError

INITIAL_REASON = "Initial default strategy (Phase 7 thresholds, versioned)."


class InvalidStateError(Exception):
    """A pending change isn't PENDING anymore (already decided) -- can't
    confirm/reject it a second time."""


class StrategyService:
    def __init__(self, db: Session):
        self.db = db
        self.versions = StrategyVersionRepository(db)
        self.pending = PendingStrategyChangeRepository(db)

    def get_active_version(self) -> StrategyVersion:
        """Bootstraps version 1 from DEFAULT_RULES the first time this is
        called on a fresh DB -- self-initializing, no migration data-seed
        required."""
        active = self.versions.get_active()
        if active is not None:
            return active
        version = self.versions.create(
            version_number=self.versions.latest_version_number() + 1,
            rules=DEFAULT_RULES.to_dict(),
            status="ACTIVE",
            change_type="AUTO_APPLIED",
            reason=INITIAL_REASON,
        )
        self.db.commit()
        return version

    def get_active_rules(self) -> SignalRules:
        return SignalRules.from_dict(self.get_active_version().rules)

    def list_versions(self) -> list[StrategyVersionRead]:
        self.get_active_version()  # ensures version 1 is bootstrapped, same as get_active_rules()
        return [version_to_read(v) for v in self.versions.list()]

    def list_pending(self, status: str | None = None) -> list[PendingStrategyChangeRead]:
        return [pending_to_read(p) for p in self.pending.list(status=status)]

    def _run_backtest(self, rules: SignalRules, price_points: Sequence | None) -> BacktestResult | None:
        return walk_forward_hit_rate(price_points, rules) if price_points else None

    @staticmethod
    def _backtest_to_dict(result: BacktestResult | None) -> dict | None:
        if result is None:
            return None
        return {
            "hits": result.hits,
            "n": result.n,
            "horizon": result.horizon,
            "deadzone_pct": str(result.deadzone_pct),
            "hit_rate": str(result.hit_rate) if result.hit_rate is not None else None,
        }

    def propose_change(
        self, proposed_rules: dict, reason: str, price_points: Sequence | None = None
    ) -> StrategyVersion | PendingStrategyChange:
        """Returns the new StrategyVersion if the change was small (applied
        immediately), or the PendingStrategyChange row if it was big
        (queued, unapplied)."""
        active = self.get_active_version()
        is_small = set(proposed_rules.keys()) == set(active.rules.keys())

        if is_small:
            self.versions.update(active, status="SUPERSEDED")
            backtest = self._run_backtest(SignalRules.from_dict(proposed_rules), price_points)
            new_version = self.versions.create(
                version_number=self.versions.latest_version_number() + 1,
                rules=proposed_rules,
                status="ACTIVE",
                change_type="AUTO_APPLIED",
                reason=reason,
                backtest_hit_rate=backtest.hit_rate if backtest is not None else None,
                backtest_n=backtest.n if backtest is not None else None,
            )
            self.db.commit()
            return new_version

        backtest_before = self._backtest_to_dict(self._run_backtest(SignalRules.from_dict(active.rules), price_points))
        backtest_after = self._backtest_to_dict(self._run_backtest(SignalRules.from_dict(proposed_rules), price_points))
        change = self.pending.create(
            proposed_rules=proposed_rules,
            reason=reason,
            backtest_before=backtest_before,
            backtest_after=backtest_after,
            status="PENDING",
        )
        self.db.commit()
        return change

    def confirm_pending(self, change_id: int) -> StrategyVersion:
        change = self.pending.get(change_id)
        if change is None:
            raise NotFoundError(f"Pending strategy change {change_id} not found.")
        if change.status != "PENDING":
            raise InvalidStateError(f"Pending strategy change {change_id} is already {change.status}.")

        active = self.get_active_version()
        self.versions.update(active, status="SUPERSEDED")
        new_version = self.versions.create(
            version_number=self.versions.latest_version_number() + 1,
            rules=change.proposed_rules,
            status="ACTIVE",
            change_type="CONFIRMED",
            reason=change.reason,
        )
        self.pending.update(change, status="CONFIRMED", decided_at=datetime.now(timezone.utc).replace(tzinfo=None))
        self.db.commit()
        return new_version

    def reject_pending(self, change_id: int) -> PendingStrategyChange:
        change = self.pending.get(change_id)
        if change is None:
            raise NotFoundError(f"Pending strategy change {change_id} not found.")
        if change.status != "PENDING":
            raise InvalidStateError(f"Pending strategy change {change_id} is already {change.status}.")
        self.pending.update(change, status="REJECTED", decided_at=datetime.now(timezone.utc).replace(tzinfo=None))
        self.db.commit()
        return change


def version_to_read(v: StrategyVersion) -> StrategyVersionRead:
    return StrategyVersionRead(
        id=v.id,
        version_number=v.version_number,
        rules=v.rules,
        status=v.status,
        change_type=v.change_type,
        reason=v.reason,
        backtest_hit_rate=str(v.backtest_hit_rate) if v.backtest_hit_rate is not None else None,
        backtest_n=v.backtest_n,
        created_at=v.created_at,
    )


def pending_to_read(p: PendingStrategyChange) -> PendingStrategyChangeRead:
    return PendingStrategyChangeRead(
        id=p.id,
        proposed_rules=p.proposed_rules,
        reason=p.reason,
        backtest_before=p.backtest_before,
        backtest_after=p.backtest_after,
        status=p.status,
        created_at=p.created_at,
        decided_at=p.decided_at,
    )
