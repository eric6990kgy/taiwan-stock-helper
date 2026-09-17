import type { AgentRole, JournalCategory, RecommendationAction, Score, SignalStatus, ThesisStatus, WatchlistStatus } from "../types/api";

export function DemoDataBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700 ring-1 ring-amber-200">
      Demo data
    </span>
  );
}

export function SnapshotBadge({ label = "Snapshot, not a time series" }: { label?: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500 ring-1 ring-slate-200">
      {label}
    </span>
  );
}

const WATCHLIST_STATUS_STYLES: Record<WatchlistStatus, string> = {
  WATCHING: "bg-slate-100 text-slate-600 ring-slate-200",
  RESEARCHING: "bg-blue-50 text-blue-700 ring-blue-200",
  CANDIDATE: "bg-amber-50 text-amber-700 ring-amber-200",
  OWNED: "bg-green-50 text-green-700 ring-green-200",
  REJECTED: "bg-red-50 text-red-600 ring-red-200",
};

export function WatchlistStatusBadge({ status }: { status: WatchlistStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${WATCHLIST_STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}

const JOURNAL_CATEGORY_LABELS: Record<JournalCategory, string> = {
  BUY_REASON: "買入理由",
  SELL_REASON: "賣出理由",
  OBSERVATION: "觀察",
  REVIEW: "檢討",
  OTHER: "其他",
};

const JOURNAL_CATEGORY_STYLES: Record<JournalCategory, string> = {
  BUY_REASON: "bg-green-50 text-green-700 ring-green-200",
  SELL_REASON: "bg-red-50 text-red-600 ring-red-200",
  OBSERVATION: "bg-blue-50 text-blue-700 ring-blue-200",
  REVIEW: "bg-amber-50 text-amber-700 ring-amber-200",
  OTHER: "bg-slate-100 text-slate-600 ring-slate-200",
};

export function JournalCategoryBadge({ category }: { category: JournalCategory }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${JOURNAL_CATEGORY_STYLES[category]}`}>
      {JOURNAL_CATEGORY_LABELS[category]}
    </span>
  );
}

export { JOURNAL_CATEGORY_LABELS };

const THESIS_STATUS_STYLES: Record<ThesisStatus, string> = {
  INTACT: "bg-green-50 text-green-700 ring-green-200",
  NEEDS_REVIEW: "bg-amber-50 text-amber-700 ring-amber-200",
  BROKEN: "bg-red-50 text-red-600 ring-red-200",
};

export function ThesisStatusBadge({ status }: { status: ThesisStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${THESIS_STATUS_STYLES[status]}`}>
      {status.replace("_", " ")}
    </span>
  );
}

const REGIME_STYLES: Record<NonNullable<Score["regime"]>, string> = {
  BULL: "bg-green-50 text-green-700 ring-green-200",
  BEAR: "bg-red-50 text-red-600 ring-red-200",
  NEUTRAL: "bg-slate-100 text-slate-600 ring-slate-200",
};

/** The TAIEX-derived market regime used to weight Phase 7's composite
 * score -- null (rendered "Regime unknown") means TAIEX history wasn't
 * available yet when this score was computed. */
export function RegimeBadge({ regime }: { regime: Score["regime"] }) {
  if (regime === null) {
    return (
      <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-400 ring-1 ring-slate-200">
        Regime unknown
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${REGIME_STYLES[regime]}`}>
      {regime}
    </span>
  );
}

const SIGNAL_STATUS_STYLES: Record<SignalStatus, string> = {
  BULLISH: "bg-green-50 text-green-700 ring-green-200",
  BEARISH: "bg-red-50 text-red-600 ring-red-200",
  NEUTRAL: "bg-slate-100 text-slate-600 ring-slate-200",
  UNAVAILABLE: "bg-slate-50 text-slate-400 ring-slate-200",
};

/** BULLISH/BEARISH/NEUTRAL/UNAVAILABLE -- a signal's own reading, never a
 * BUY/SELL instruction (Phase 7 Part 2). Shared by SignalsPanel for both
 * the per-signal badges and the "Overall" summary badge. */
export function SignalStatusBadge({ status }: { status: SignalStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${SIGNAL_STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}

const ACTION_LABELS: Record<RecommendationAction, string> = {
  CONSIDER_INCREASE: "Consider Increasing",
  CONSIDER_DECREASE: "Consider Decreasing",
  WATCH: "Watch",
};

const ACTION_STYLES: Record<RecommendationAction, string> = {
  CONSIDER_INCREASE: "bg-green-50 text-green-700 ring-green-200",
  CONSIDER_DECREASE: "bg-red-50 text-red-600 ring-red-200",
  WATCH: "bg-slate-100 text-slate-600 ring-slate-200",
};

/** Conditional language only (個股訊號引擎規格書 Phase B) -- never a BUY/SELL
 * instruction. Phase 8's Recommendation.action. */
export function ActionBadge({ action }: { action: RecommendationAction }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${ACTION_STYLES[action]}`}>
      {ACTION_LABELS[action]}
    </span>
  );
}

/** Whether a scored RecommendationOutcome's call turned out right (Phase
 * 10) -- a ground-truth label, not a live reading, so it's styled
 * distinctly from SignalStatusBadge even though it also uses green/red. */
export function HitMissBadge({ hit }: { hit: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${
        hit ? "bg-green-50 text-green-700 ring-green-200" : "bg-red-50 text-red-600 ring-red-200"
      }`}
    >
      {hit ? "Hit" : "Miss"}
    </span>
  );
}

export const AGENT_ROLE_LABELS: Record<AgentRole, string> = {
  FUNDAMENTAL_ANALYST: "基本面研究員",
  TECHNICAL_ANALYST: "技術面研究員",
  PORTFOLIO_MANAGER: "投資組合經理人",
};

/** Labels for AgentAnalysis.details' keys -- the field set differs per
 * role (see AgentResearchService's per-role Pydantic schemas), so this
 * is one flat lookup covering every role's fields rather than three
 * separate maps. An unrecognized key (a future field this map hasn't
 * been updated for yet) falls back to showing the raw key. */
export const AGENT_DETAIL_FIELD_LABELS: Record<string, string> = {
  revenue_trend: "營收動能",
  profitability: "獲利能力",
  cash_flow_and_balance: "現金流",
  trend: "均線結構",
  momentum: "動能指標",
  institutional_flow: "籌碼動向",
  agreement_with_fundamental: "同意基本面",
  agreement_with_technical: "同意技術面",
  stance_vs_system: "與系統判斷",
  key_risk: "主要風險",
};

/** Must never look like an ordinary recommendation at a glance (spec
 * requirement) -- a distinct, loud treatment, not just another badge lost
 * in a row of others. */
export function RiskBlockedBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 ring-1 ring-amber-300">
      ⚠ Risk Blocked
    </span>
  );
}
