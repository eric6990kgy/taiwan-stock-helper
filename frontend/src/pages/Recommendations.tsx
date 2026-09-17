import { useState } from "react";
import { ActionBadge, AGENT_DETAIL_FIELD_LABELS, AGENT_ROLE_LABELS, RiskBlockedBadge, SignalStatusBadge } from "../components/Badges";
import { QueryState } from "../components/QueryState";
import { useRecommendations } from "../features/recommendations/hooks";
import { formatMoney } from "../utils/decimal";
import type { AgentAnalysis, Recommendation } from "../types/api";

/** Every recommendation here already changed status since the last scan
 * (an unchanged ticker never appears) and, for CONSIDER_INCREASE, already
 * passed -- or was blocked by -- Phase A's risk/drawdown gate before this
 * list was ever populated (個股訊號引擎規格書 Phase B). Nothing here is a
 * BUY/SELL instruction; execution is entirely manual. */
export function Recommendations() {
  const recommendationsQuery = useRecommendations();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Recommendations</h1>
        <p className="text-sm text-slate-500">
          Tickers whose signal status changed on the most recent "Update Market Data" run, risk-checked before being shown.
        </p>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <QueryState
          isLoading={recommendationsQuery.isLoading}
          isError={recommendationsQuery.isError}
          error={recommendationsQuery.error}
          data={recommendationsQuery.data}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No recommendations yet."
          emptyHint='Run "Update Market Data" in Settings to scan your watchlist for signal changes.'
        >
          {(recommendations) => (
            <div className="flex flex-col divide-y divide-slate-100">
              {recommendations.map((rec) => (
                <RecommendationRow key={rec.id} rec={rec} />
              ))}
            </div>
          )}
        </QueryState>
      </section>
    </div>
  );
}

function RecommendationRow({ rec }: { rec: Recommendation }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`px-3 py-3 ${rec.risk_blocked ? "bg-amber-50/60" : ""}`}>
      <button type="button" onClick={() => setExpanded((e) => !e)} className="flex w-full flex-wrap items-center gap-2 text-left">
        <span className="font-medium text-slate-900">{rec.ticker}</span>
        <span className="text-sm text-slate-400">{rec.asset_name}</span>
        <ActionBadge action={rec.action} />
        {rec.risk_blocked && <RiskBlockedBadge />}
        <span className="ml-auto flex items-center gap-1 text-xs text-slate-400">
          {rec.previous_status ?? "—"} → <SignalStatusBadge status={rec.new_status} />
        </span>
      </button>

      {expanded && (
        <div className="mt-3 flex flex-col gap-3 text-sm">
          {rec.risk_blocked && (
            <p className="rounded-md bg-amber-100 px-3 py-2 text-amber-900">{rec.risk_block_reason}</p>
          )}

          <div>
            <p className="mb-1 text-xs font-medium text-slate-500">Triggered Signals</p>
            <div className="flex flex-col gap-1">
              {rec.triggered_signals.map((s) => (
                <div key={s.id} className="flex items-center gap-2 text-xs">
                  <SignalStatusBadge status={s.status} />
                  <span className="text-slate-600">{s.explanation}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-slate-400">
            {rec.composite_score !== null && (
              <>
                Composite {formatMoney(rec.composite_score, 1)}/100
                {rec.regime && ` · Regime ${rec.regime}`}
                {" · "}
              </>
            )}
            {new Date(rec.created_at).toLocaleString()}
          </p>

          {rec.agent_analyses.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-slate-500">Agent Research Opinions</p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {rec.agent_analyses.map((a) => (
                  <AgentAnalysisCard key={a.role} analysis={a} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AgentAnalysisCard({ analysis }: { analysis: AgentAnalysis }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-slate-200 bg-slate-50 p-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-slate-700">{AGENT_ROLE_LABELS[analysis.role]}</span>
        <span className="flex items-center gap-1">
          <SignalStatusBadge status={analysis.call} />
          <span className="text-xs text-slate-400">{analysis.confidence}%</span>
        </span>
      </div>
      <table className="text-xs">
        <tbody>
          {Object.entries(analysis.details).map(([key, value]) => (
            <tr key={key}>
              <td className={`whitespace-nowrap py-0.5 pr-2 align-top ${key === "key_risk" ? "text-red-500" : "text-slate-400"}`}>
                {AGENT_DETAIL_FIELD_LABELS[key] ?? key}
              </td>
              <td className={`py-0.5 align-top ${key === "key_risk" ? "text-red-600" : "text-slate-600"}`}>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
