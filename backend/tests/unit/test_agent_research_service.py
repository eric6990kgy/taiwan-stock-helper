"""AgentResearchService tests (Phase 12) -- fakes both GeminiClient and
ResearchService (a full network+DB round trip belongs to GeminiClient's
own tests and ResearchService's own tests respectively); this file is
scoped to the orchestration logic: per-role failure isolation, the
disabled-client no-op, and that the Portfolio Manager's prompt genuinely
carries the other two roles' output plus the deterministic decision.
"""

from types import SimpleNamespace

from app.models.asset import Asset
from app.models.recommendation import Recommendation
from app.services.agent_research_service import (
    FUNDAMENTAL_ANALYST,
    PORTFOLIO_MANAGER,
    TECHNICAL_ANALYST,
    AgentResearchService,
)
from app.services.gemini_client import GeminiAnalysisError
from app.services.recommendation_service import ScanOutcome
from app.services.strategy_service import StrategyService


class FakeGeminiClient:
    """Roles are identified by call ORDER, not by sniffing keywords out of
    the system_instruction text -- the PM's own prompt legitimately
    mentions "基本面研究員"/"技術面研究員" as part of describing its job,
    so a substring match would misattribute its call. analyze() always
    calls fundamental -> technical -> pm, in that fixed sequence."""

    _ROLE_ORDER = (FUNDAMENTAL_ANALYST, TECHNICAL_ANALYST, PORTFOLIO_MANAGER)

    def __init__(self, fail_roles: tuple[str, ...] = ()):
        self.enabled = True
        self.fail_roles = set(fail_roles)
        self.calls: list[dict] = []

    def structured_call(self, *, system_instruction, input, schema, model=None):
        role = self._ROLE_ORDER[len(self.calls)]
        self.calls.append({"role": role, "input": input})
        if role in self.fail_roles:
            raise GeminiAnalysisError(f"{role} failed")
        # Each role has its own schema/field set now -- fill whatever
        # fields it declares beyond call/confidence generically, so this
        # fake doesn't need to know FundamentalCallSchema's fields differ
        # from TechnicalCallSchema's/PortfolioManagerCallSchema's.
        extra = {name: f"{role} {name}" for name in schema.model_fields if name not in ("call", "confidence")}
        return schema(call="BULLISH", confidence=70, **extra)


class DisabledGeminiClient:
    enabled = False

    def structured_call(self, **kwargs):
        raise AssertionError("must never be called when disabled")


class FakeResearchService:
    def get_fundamentals(self, ticker):
        return []

    def get_monthly_revenue(self, ticker):
        return []

    def get_score(self, ticker):
        return None

    def get_technical_indicators(self, ticker):
        return SimpleNamespace(model_dump=lambda mode=None: {"rsi_14": "50"})

    def get_institutional_flows(self, ticker, range_key=None):
        return []

    def get_margin_trading(self, ticker, range_key=None):
        return []


def make_outcome(db) -> ScanOutcome:
    asset = Asset(ticker="2330", name="Test Co", asset_type="STOCK", currency="TWD", is_demo_data=False)
    db.add(asset)
    db.flush()
    strategy_version_id = StrategyService(db).get_active_version().id
    rec = Recommendation(
        asset_id=asset.id,
        strategy_version_id=strategy_version_id,
        action="CONSIDER_INCREASE",
        previous_status="NEUTRAL",
        new_status="BULLISH",
        triggered_signals=[{"id": "SMA20", "category": "TECHNICAL", "name": "SMA20", "status": "BULLISH", "explanation": "x"}],
        risk_blocked=False,
    )
    db.add(rec)
    db.flush()
    return ScanOutcome(recommendation=rec, ticker=asset.ticker, asset_name=asset.name, composite_score=None, regime=None)


def test_disabled_client_returns_nothing_and_persists_nothing(db_session):
    outcome = make_outcome(db_session)
    service = AgentResearchService(db_session, DisabledGeminiClient(), FakeResearchService())

    persisted, errors = service.analyze(outcome)

    assert persisted == []
    assert errors == []


def test_all_three_roles_succeed_and_persist(db_session):
    outcome = make_outcome(db_session)
    gemini = FakeGeminiClient()
    service = AgentResearchService(db_session, gemini, FakeResearchService())

    persisted, errors = service.analyze(outcome)

    assert errors == []
    assert {row.role for row in persisted} == {FUNDAMENTAL_ANALYST, TECHNICAL_ANALYST, PORTFOLIO_MANAGER}
    assert all(row.recommendation_id == outcome.recommendation.id for row in persisted)


def test_one_roles_failure_does_not_lose_the_other_two(db_session):
    outcome = make_outcome(db_session)
    gemini = FakeGeminiClient(fail_roles=(TECHNICAL_ANALYST,))
    service = AgentResearchService(db_session, gemini, FakeResearchService())

    persisted, errors = service.analyze(outcome)

    assert {row.role for row in persisted} == {FUNDAMENTAL_ANALYST, PORTFOLIO_MANAGER}
    assert len(errors) == 1
    assert TECHNICAL_ANALYST in errors[0]


def test_portfolio_manager_prompt_includes_the_other_two_roles_and_the_system_decision(db_session):
    outcome = make_outcome(db_session)
    gemini = FakeGeminiClient()
    service = AgentResearchService(db_session, gemini, FakeResearchService())

    service.analyze(outcome)

    pm_call = next(c for c in gemini.calls if c["role"] == PORTFOLIO_MANAGER)
    assert "CONSIDER_INCREASE" in pm_call["input"]
    assert "fundamental_analyst" in pm_call["input"]
    assert "technical_analyst" in pm_call["input"]
    assert "BULLISH" in pm_call["input"]  # the other two roles' own call, and new_status


def test_pm_still_runs_even_when_fundamental_and_technical_both_fail(db_session):
    """The PM role's own context handles a None analyst gracefully instead
    of crashing -- it should still produce its own independent opinion."""
    outcome = make_outcome(db_session)
    gemini = FakeGeminiClient(fail_roles=(FUNDAMENTAL_ANALYST, TECHNICAL_ANALYST))
    service = AgentResearchService(db_session, gemini, FakeResearchService())

    persisted, errors = service.analyze(outcome)

    assert {row.role for row in persisted} == {PORTFOLIO_MANAGER}
    assert len(errors) == 2
