import { useState } from "react";
import { ActionBadge, AGENT_ROLE_LABELS, HitMissBadge, RiskBlockedBadge, SignalStatusBadge } from "../components/Badges";
import { useAgentPerformance } from "../features/agentPerformance/hooks";
import { QueryState } from "../components/QueryState";
import { SummaryCard } from "../components/SummaryCard";
import { useReviewOutcomes, useReviewSummary } from "../features/review/hooks";
import { formatMoney } from "../utils/decimal";
import type { AgentRole, RecommendationOutcome, ReviewSummary as ReviewSummaryType } from "../types/api";

const AGENT_ROLES: AgentRole[] = ["FUNDAMENTAL_ANALYST", "TECHNICAL_ANALYST", "PORTFOLIO_MANAGER"];

/** Ground-truth hit-rate for past recommendations (複盤, Phase 10) -- did
 * price actually move the direction each CONSIDER_INCREASE/
 * CONSIDER_DECREASE call implied, some trading days later? Scored
 * retroactively and best-effort every time "Update Market Data" runs
 * (RecommendationOutcomeService); a recommendation with no outcome row
 * yet simply hasn't reached its check-in horizon, never a fabricated
 * result. */
export function Review() {
  const overallQuery = useReviewSummary();
  const increaseQuery = useReviewSummary("CONSIDER_INCREASE");
  const decreaseQuery = useReviewSummary("CONSIDER_DECREASE");
  const outcomesQuery = useReviewOutcomes();
  const fundamentalQuery = useAgentPerformance("FUNDAMENTAL_ANALYST");
  const technicalQuery = useAgentPerformance("TECHNICAL_ANALYST");
  const pmQuery = useAgentPerformance("PORTFOLIO_MANAGER");
  const agentQueries: Record<AgentRole, ReturnType<typeof useAgentPerformance>> = {
    FUNDAMENTAL_ANALYST: fundamentalQuery,
    TECHNICAL_ANALYST: technicalQuery,
    PORTFOLIO_MANAGER: pmQuery,
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Review</h1>
        <p className="text-sm text-slate-500">
          How past recommendations actually turned out -- never a fabricated rate when the sample is too small.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <SummaryCardFromReview title="Overall Hit Rate" query={overallQuery} />
        <SummaryCardFromReview title="Consider Increase" query={increaseQuery} />
        <SummaryCardFromReview title="Consider Decrease" query={decreaseQuery} />
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Agent Performance</h2>
        <p className="mb-3 text-xs text-slate-500">
          Each Gemini agent's own call, scored the same way as the deterministic engine above -- a research opinion, not a decision.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {AGENT_ROLES.map((role) => (
            <SummaryCardFromReview key={role} title={AGENT_ROLE_LABELS[role]} query={agentQueries[role]} />
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Scored Outcomes</h2>
        <QueryState
          isLoading={outcomesQuery.isLoading}
          isError={outcomesQuery.isError}
          error={outcomesQuery.error}
          data={outcomesQuery.data}
          isEmpty={(d) => d.length === 0}
          emptyTitle="Nothing scored yet."
          emptyHint='Recommendations are scored automatically once enough trading days have passed since they fired -- check back after "Update Market Data" has run a few more times.'
        >
          {(outcomes) => (
            <div className="flex flex-col divide-y divide-slate-100">
              {outcomes.map((o) => (
                <OutcomeRow key={o.id} outcome={o} />
              ))}
            </div>
          )}
        </QueryState>
      </section>
    </div>
  );
}

function SummaryCardFromReview({ title, query }: { title: string; query: { data?: ReviewSummaryType; isLoading: boolean } }) {
  if (query.isLoading || !query.data) {
    return <SummaryCard label={title} value="…" />;
  }
  const { hit_rate, hits, n } = query.data;
  if (hit_rate === null) {
    return <SummaryCard label={title} value="insufficient sample" />;
  }
  return <SummaryCard label={title} value={`${formatMoney(String(Number(hit_rate) * 100), 1)}% (${hits}/${n})`} />;
}

function OutcomeRow({ outcome }: { outcome: RecommendationOutcome }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="px-3 py-3">
      <button type="button" onClick={() => setExpanded((e) => !e)} className="flex w-full flex-wrap items-center gap-2 text-left">
        <span className="font-medium text-slate-900">{outcome.ticker}</span>
        <span className="text-sm text-slate-400">{outcome.asset_name}</span>
        <ActionBadge action={outcome.action} />
        {outcome.risk_blocked && <RiskBlockedBadge />}
        <span className="ml-auto">
          <HitMissBadge hit={outcome.hit} />
        </span>
      </button>

      {expanded && (
        <div className="mt-3 flex flex-col gap-2 text-sm">
          <p className="text-slate-600">
            Called <SignalStatusBadge status={outcome.call} /> on {outcome.as_of_date} -- actually{" "}
            <SignalStatusBadge status={outcome.actual_direction} /> by {outcome.outcome_date} (
            {outcome.horizon_trading_days} trading days later).
          </p>
          <p className="text-xs text-slate-400">
            {outcome.from_close} → {outcome.to_close} · Scored {new Date(outcome.computed_at).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  );
}
