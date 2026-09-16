import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { RegimeBadge } from "./Badges";
import type { Score } from "../types/api";
import { formatMoney } from "../utils/decimal";

interface CompositeScorePanelProps {
  score: Score | null;
  history: Score[];
}

const SUB_SCORE_FIELDS: { key: keyof Score; label: string }[] = [
  { key: "value_score", label: "Value" },
  { key: "growth_score", label: "Growth" },
  { key: "momentum_score", label: "Momentum" },
  { key: "quality_score", label: "Quality" },
];

/** Phase 7 composite score -- every number here is pre-computed by the
 * backend (app.analytics.scoring); this component only formats, labels,
 * and charts it. A missing sub-score renders "-" (per missing_components),
 * never a fabricated 0. */
export function CompositeScorePanel({ score, history }: CompositeScorePanelProps) {
  if (score === null) {
    return <p className="text-sm text-slate-400">No composite score computed yet for this ticker.</p>;
  }

  const chartData = history
    .filter((h) => h.composite_score !== null)
    .map((h) => ({ date: h.date, composite: Number(h.composite_score) }));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <p className="text-xs text-slate-400">Composite</p>
          <p className="text-2xl font-semibold tabular-nums text-slate-900">
            <span>{score.composite_score !== null ? formatMoney(score.composite_score, 1) : "—"}</span>
            <span className="text-sm font-normal text-slate-400"> / 100</span>
          </p>
        </div>
        <RegimeBadge regime={score.regime} />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {SUB_SCORE_FIELDS.map(({ key, label }) => {
          const raw = score[key] as string | null;
          const value = raw !== null ? Number(raw) : null;
          return (
            <div key={key}>
              <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                <span>{label}</span>
                <span className="tabular-nums">{value !== null ? formatMoney(raw, 1) : "—"}</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-100">
                <div
                  className="h-1.5 rounded-full bg-blue-500"
                  style={{ width: value !== null ? `${value}%` : "0%" }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {chartData.length > 1 && (
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={24} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} width={28} />
            <Tooltip formatter={(value) => [typeof value === "number" ? value.toFixed(1) : "—", "Composite"]} />
            <Line type="monotone" dataKey="composite" stroke="#2563eb" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}

      <p className="text-xs text-slate-400">
        As of {score.date}. Source: {score.source}
        {score.missing_components.length > 0 && ` — missing: ${score.missing_components.join(", ")}`}
      </p>
    </div>
  );
}
