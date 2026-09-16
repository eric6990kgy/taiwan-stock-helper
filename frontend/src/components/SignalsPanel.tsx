import { useState } from "react";
import type { Signal, SignalResult } from "../types/api";
import { SignalStatusBadge } from "./Badges";
import { formatMoney } from "../utils/decimal";

const CATEGORY_LABELS: Record<Signal["category"], string> = {
  TECHNICAL: "Technical",
  INSTITUTIONAL: "Institutional",
  FUNDAMENTAL: "Fundamental",
  COMPOSITE: "Composite",
};

const CATEGORY_ORDER: Signal["category"][] = ["TECHNICAL", "INSTITUTIONAL", "FUNDAMENTAL", "COMPOSITE"];

/** A signal is NOT an investment recommendation -- BULLISH/BEARISH describe
 * an indicator's own reading, never a BUY/SELL instruction (shown in the
 * disclaimer below, not just in code comments). Computed on demand: there
 * is no history to chart here, unlike CompositeScorePanel. */
export function SignalsPanel({ data }: { data: SignalResult }) {
  const byCategory = CATEGORY_ORDER.map((category) => ({
    category,
    signals: data.signals.filter((s) => s.category === category),
  })).filter((g) => g.signals.length > 0);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Overall</span>
          <SignalStatusBadge status={data.overall_status} />
        </div>
        {data.as_of && <p className="text-xs text-slate-400">As of {data.as_of}</p>}
      </div>

      <div className="flex flex-col gap-3">
        {byCategory.map(({ category, signals }) => (
          <div key={category}>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">{CATEGORY_LABELS[category]}</p>
            <div className="flex flex-col divide-y divide-slate-100 rounded-lg border border-slate-200">
              {signals.map((signal) => (
                <SignalRow key={signal.id} signal={signal} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-400">
        Signals describe each indicator's own reading -- they are not investment recommendations, and never a buy/sell instruction.
      </p>
    </div>
  );
}

function SignalRow({ signal }: { signal: Signal }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="px-3 py-2">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="text-sm text-slate-700">{signal.name}</span>
        <SignalStatusBadge status={signal.status} />
      </button>
      {expanded && (
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-500 sm:grid-cols-4">
          <div>
            <p className="text-slate-400">Value</p>
            <p className="tabular-nums text-slate-700">{signal.value !== null ? formatMoney(signal.value, 2) : "—"}</p>
          </div>
          <div>
            <p className="text-slate-400">Threshold</p>
            <p className="tabular-nums text-slate-700">{signal.threshold !== null ? formatMoney(signal.threshold, 2) : "—"}</p>
          </div>
          <div>
            <p className="text-slate-400">As of</p>
            <p className="text-slate-700">{signal.as_of ?? "—"}</p>
          </div>
          <div className="col-span-2 sm:col-span-4">
            <p className="text-slate-400">Explanation</p>
            <p className="text-slate-700">{signal.explanation}</p>
          </div>
        </div>
      )}
    </div>
  );
}
