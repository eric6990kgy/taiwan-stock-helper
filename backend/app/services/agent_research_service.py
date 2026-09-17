"""Gemini multi-agent research team (Phase 12) -- three role-scoped
opinions riding alongside a deterministic Phase 8 Recommendation, never
replacing it. Reuses ResearchService's existing data-access methods for
prompt context (no new queries): fundamentals/monthly revenue/score for
the Fundamental Analyst, technical indicators/institutional flow/margin
trading for the Technical Analyst. The Portfolio Manager sees the other
two roles' own output plus the already-decided deterministic action --
framed explicitly as fixed context it can discuss but never change.

Each role has its OWN structured-output schema (a handful of short,
labeled fields) instead of one free-text paragraph -- requested by the
user after seeing the first real output: a wall of prose reads fine once
but doesn't scan like a real research report. `call`/`confidence` stay
common to all three; the rest are short (one-sentence) fields specific
to what that role actually evaluates.

Every role call is independently best-effort: one role failing (a
malformed Gemini response, a transient API error) must never lose the
other two -- see analyze()'s per-role try/except.
"""

import json
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.repositories.agent_analysis_repository import AgentAnalysisRepository
from app.services.gemini_client import DEFAULT_MODEL, GeminiAnalysisError, GeminiClient
from app.services.recommendation_service import ScanOutcome
from app.services.research_service import ResearchService

FUNDAMENTAL_ANALYST = "FUNDAMENTAL_ANALYST"
TECHNICAL_ANALYST = "TECHNICAL_ANALYST"
PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"

Call = Literal["BULLISH", "BEARISH", "NEUTRAL", "UNAVAILABLE"]


class FundamentalCallSchema(BaseModel):
    """`call` reuses Signal's own BULLISH/BEARISH/NEUTRAL/UNAVAILABLE
    vocabulary -- UNAVAILABLE for "my own inputs are too sparse to have a
    real view", never a fabricated opinion. Every other field is one
    short sentence, not a paragraph -- meant to render as a labeled row
    in a report card, not prose."""

    call: Call
    confidence: int
    revenue_trend: str
    profitability: str
    cash_flow_and_balance: str
    key_risk: str


class TechnicalCallSchema(BaseModel):
    call: Call
    confidence: int
    trend: str
    momentum: str
    institutional_flow: str
    key_risk: str


class PortfolioManagerCallSchema(BaseModel):
    call: Call
    confidence: int
    agreement_with_fundamental: str
    agreement_with_technical: str
    stance_vs_system: str
    key_risk: str


_BOUNDARY = (
    "你是台股個人投資研究團隊的一員，你的輸出只是研究意見，"
    "絕對不是買賣指令，且無法覆蓋系統既有的風控/訊號判斷。"
    "請使用有條件的語氣（例如「值得留意」「風險在於」），"
    "不要使用「買進」「賣出」等指令性字眼。"
    "如果可用資料太少而無法形成判斷，call 請回答 UNAVAILABLE，不要硬湊一個意見。"
    "每個欄位只寫一句話（15-30字），不要寫成一整段文字——這些欄位是要放進報表的固定欄位，不是文章。"
)

_FUNDAMENTAL_SYSTEM_INSTRUCTION = (
    f"{_BOUNDARY}\n"
    "你的角色是基本面研究員，請根據提供的財報數據（營收成長、毛利率、ROE、"
    "現金流等）與月營收數據，評估公司基本面偏多、偏空或中性。"
    "revenue_trend 只寫營收/成長動能一句話，profitability 只寫毛利率/營益率/ROE一句話，"
    "cash_flow_and_balance 只寫現金流/負債結構一句話，key_risk 只寫主要風險一句話。"
)

_TECHNICAL_SYSTEM_INSTRUCTION = (
    f"{_BOUNDARY}\n"
    "你的角色是技術面研究員，請根據提供的技術指標（均線、RSI、MACD、布林通道）"
    "與籌碼面資料（三大法人買賣超、融資融券），評估短中期技術面偏多、偏空或中性。"
    "trend 只寫均線/價格結構一句話，momentum 只寫RSI/MACD/KD動能一句話，"
    "institutional_flow 只寫外資/投信/融資動向一句話，key_risk 只寫主要風險一句話。"
)

_PM_SYSTEM_INSTRUCTION = (
    f"{_BOUNDARY}\n"
    "你的角色是投資組合經理人，負責綜合基本面研究員與技術面研究員的意見。"
    "你會同時看到系統既有的風控/訊號判斷（action/new_status/triggered_signals/"
    "risk_blocked）——這是已經做成的系統決策，你可以評論或不同意它，"
    "但你的輸出永遠不會、也不能改變它。請給出你自己獨立的研究意見。"
    "agreement_with_fundamental 只寫是否同意基本面研究員+一句原因，"
    "agreement_with_technical 只寫是否同意技術面研究員+一句原因，"
    "stance_vs_system 只寫你的立場跟系統判斷是否一致+一句原因，key_risk 只寫主要風險一句話。"
)


class AgentResearchService:
    """`research`'s existing data-access methods already surface the raw
    inputs each deterministic Signal is itself derived from (SMA/RSI/MACD,
    institutional flow, revenue growth, composite score) -- there's
    nothing SignalService.get_signals() would add for the analyst roles
    that isn't already in that context or, for the PM role, already
    summarized in the Recommendation's own triggered_signals."""

    def __init__(self, db: Session, gemini: GeminiClient, research: ResearchService):
        self.gemini = gemini
        self.research = research
        self.repo = AgentAnalysisRepository(db)

    def analyze(self, outcome: ScanOutcome) -> tuple[list, list[str]]:
        """Returns ([], []) immediately (persists nothing) if Gemini isn't
        configured -- this whole phase is inert until GEMINI_API_KEY is
        set, same convention as LineNotifier.enabled. Never raises: each
        role's failure is isolated (one bad response must never lose the
        other two) and reported back as a plain error message for the
        caller (market_data_service) to record as a best-effort warning,
        exactly like a LineNotifyError one loop up.
        """
        if not self.gemini.enabled:
            return [], []

        ticker = outcome.ticker
        recommendation = outcome.recommendation
        errors: list[str] = []

        fundamental = self._safe_role(FUNDAMENTAL_ANALYST, lambda: self._run_fundamental(ticker), errors)
        technical = self._safe_role(TECHNICAL_ANALYST, lambda: self._run_technical(ticker), errors)
        pm = self._safe_role(
            PORTFOLIO_MANAGER, lambda: self._run_pm(ticker, recommendation, fundamental, technical), errors
        )

        persisted = []
        for role, result in ((FUNDAMENTAL_ANALYST, fundamental), (TECHNICAL_ANALYST, technical), (PORTFOLIO_MANAGER, pm)):
            if result is None:
                continue
            row = self.repo.create(
                recommendation_id=recommendation.id,
                role=role,
                call=result.call,
                confidence=result.confidence,
                details=result.model_dump(exclude={"call", "confidence"}),
                model=DEFAULT_MODEL,
            )
            persisted.append(row)

        return persisted, errors

    def _safe_role(self, role: str, fn, errors: list[str]):
        try:
            return fn()
        except GeminiAnalysisError as exc:
            errors.append(f"{role}: {exc}")
            return None

    def _run_fundamental(self, ticker: str) -> FundamentalCallSchema:
        fundamentals = self.research.get_fundamentals(ticker)
        revenue = self.research.get_monthly_revenue(ticker)
        score = self.research.get_score(ticker)
        context = {
            "ticker": ticker,
            "fundamentals": [f.model_dump(mode="json") for f in fundamentals[-4:]],
            "monthly_revenue": [r.model_dump(mode="json") for r in revenue[-6:]],
            "composite_score": score.model_dump(mode="json") if score is not None else None,
        }
        return self.gemini.structured_call(
            system_instruction=_FUNDAMENTAL_SYSTEM_INSTRUCTION,
            input=json.dumps(context, ensure_ascii=False, default=str),
            schema=FundamentalCallSchema,
        )

    def _run_technical(self, ticker: str) -> TechnicalCallSchema:
        indicators = self.research.get_technical_indicators(ticker)
        flows = self.research.get_institutional_flows(ticker, range_key="1M")
        margin = self.research.get_margin_trading(ticker, range_key="1M")
        context = {
            "ticker": ticker,
            "technical_indicators": indicators.model_dump(mode="json"),
            "institutional_flows": [f.model_dump(mode="json") for f in flows],
            "margin_trading": [m.model_dump(mode="json") for m in margin],
        }
        return self.gemini.structured_call(
            system_instruction=_TECHNICAL_SYSTEM_INSTRUCTION,
            input=json.dumps(context, ensure_ascii=False, default=str),
            schema=TechnicalCallSchema,
        )

    def _run_pm(
        self,
        ticker: str,
        recommendation,
        fundamental: FundamentalCallSchema | None,
        technical: TechnicalCallSchema | None,
    ) -> PortfolioManagerCallSchema:
        context = {
            "ticker": ticker,
            "system_decision": {
                "action": recommendation.action,
                "previous_status": recommendation.previous_status,
                "new_status": recommendation.new_status,
                "triggered_signals": recommendation.triggered_signals,
                "risk_blocked": recommendation.risk_blocked,
                "risk_block_reason": recommendation.risk_block_reason,
            },
            "fundamental_analyst": fundamental.model_dump() if fundamental is not None else None,
            "technical_analyst": technical.model_dump() if technical is not None else None,
        }
        return self.gemini.structured_call(
            system_instruction=_PM_SYSTEM_INSTRUCTION,
            input=json.dumps(context, ensure_ascii=False, default=str),
            schema=PortfolioManagerCallSchema,
        )
