import type { ReactNode } from "react";
import { SIGN_TEXT_CLASS, type Sign } from "../utils/decimal";

interface SummaryCardProps {
  label: string;
  value: string;
  sign?: Sign;
  subValue?: string;
  hint?: ReactNode;
}

export function SummaryCard({ label, value, sign = "neutral", subValue, hint }: SummaryCardProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
        {hint}
      </div>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${SIGN_TEXT_CLASS[sign]}`}>{value}</p>
      {subValue && <p className="mt-1 text-xs text-slate-400">{subValue}</p>}
    </div>
  );
}
