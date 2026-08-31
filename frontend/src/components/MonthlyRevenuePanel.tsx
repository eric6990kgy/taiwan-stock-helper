import type { MonthlyRevenue } from "../types/api";
import { Money, Percent } from "./Money";

interface MonthlyRevenuePanelProps {
  rows: MonthlyRevenue[];
}

/** 月營收 (monthly revenue) with YoY/MoM growth -- growth is computed by the
 * backend on read and comes through as null (rendered "—") whenever the
 * comparison period is missing, never a fabricated 0%. */
export function MonthlyRevenuePanel({ rows }: MonthlyRevenuePanelProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-400">No monthly revenue data ingested yet for this ticker.</p>;
  }

  const descending = [...rows].reverse();

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="text-xs text-slate-400">
            <th className="py-1 pr-3 font-medium">Month</th>
            <th className="py-1 pr-3 font-medium">Revenue</th>
            <th className="py-1 pr-3 font-medium">YoY</th>
            <th className="py-1 pr-3 font-medium">MoM</th>
          </tr>
        </thead>
        <tbody>
          {descending.map((r) => (
            <tr key={`${r.revenue_year}-${r.revenue_month}`} className="border-t border-slate-100">
              <td className="py-1 pr-3 tabular-nums text-slate-700">
                {r.revenue_year}-{String(r.revenue_month).padStart(2, "0")}
              </td>
              <td className="py-1 pr-3">
                <Money value={r.revenue} decimals={0} />
              </td>
              <td className="py-1 pr-3">
                <Percent value={r.yoy_growth} />
              </td>
              <td className="py-1 pr-3">
                <Percent value={r.mom_growth} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-400">Source: {rows[rows.length - 1].source}</p>
    </div>
  );
}
