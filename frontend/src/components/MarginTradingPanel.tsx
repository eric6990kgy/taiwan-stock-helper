import type { MarginTrading } from "../types/api";
import { Count } from "./Money";

interface MarginTradingPanelProps {
  rows: MarginTrading[];
}

/** 融資融券 (margin purchase / short sale) -- latest-day balances plus a
 * compact recent-days table. All figures are in 張 (board lots), per the
 * backend's MarginTradingDTO docstring. */
export function MarginTradingPanel({ rows }: MarginTradingPanelProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-400">No margin trading data ingested yet for this ticker.</p>;
  }

  const latest = rows[rows.length - 1];
  const recent = rows.slice(-10).reverse();

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs text-slate-400">融資餘額 Margin Balance</p>
          <p className="text-sm font-semibold">
            <Count value={latest.margin_balance} /> <span className="text-xs font-normal text-slate-400">張</span>
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs text-slate-400">融券餘額 Short Sale Balance</p>
          <p className="text-sm font-semibold">
            <Count value={latest.short_sale_balance} /> <span className="text-xs font-normal text-slate-400">張</span>
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs text-slate-400">融資買進 Margin Buy</p>
          <p className="text-sm font-semibold">
            <Count value={latest.margin_buy} />
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs text-slate-400">融券賣出 Short Sell</p>
          <p className="text-sm font-semibold">
            <Count value={latest.short_sale_sell} />
          </p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-slate-400">
              <th className="py-1 pr-3 font-medium">Date</th>
              <th className="py-1 pr-3 font-medium">Margin Balance</th>
              <th className="py-1 pr-3 font-medium">Short Balance</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((r) => (
              <tr key={r.date} className="border-t border-slate-100">
                <td className="py-1 pr-3 tabular-nums text-slate-600">{r.date}</td>
                <td className="py-1 pr-3">
                  <Count value={r.margin_balance} />
                </td>
                <td className="py-1 pr-3">
                  <Count value={r.short_sale_balance} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-400">
        All figures in 張 (board lots, 1,000 shares). Latest as of {latest.date}. Source: {latest.source}
      </p>
    </div>
  );
}
