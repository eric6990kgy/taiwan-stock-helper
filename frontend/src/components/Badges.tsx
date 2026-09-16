import type { RecommendationAction, Score, SignalStatus, ThesisStatus, WatchlistStatus } from "../types/api";

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
