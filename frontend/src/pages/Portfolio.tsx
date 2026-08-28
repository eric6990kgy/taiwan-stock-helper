import { useState } from "react";
import { AllocationChart } from "../components/AllocationChart";
import { Money, Percent, Shares } from "../components/Money";
import { QueryState } from "../components/QueryState";
import { SummaryCard } from "../components/SummaryCard";
import { useAccounts } from "../features/transactions/hooks";
import { useAllocation, useHoldings, usePortfolioSummary, useRisk } from "../features/portfolio/hooks";
import { formatCurrency, signOf } from "../utils/decimal";

export function Portfolio() {
  const [accountId, setAccountId] = useState<number | undefined>(undefined);

  const accountsQuery = useAccounts();
  const summaryQuery = usePortfolioSummary();
  const holdingsQuery = useHoldings(accountId);
  const allocationQuery = useAllocation();
  const riskQuery = useRisk();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Portfolio</h1>
        <p className="text-sm text-slate-500">Holdings, allocation, and concentration risk.</p>
      </div>

      <QueryState
        isLoading={summaryQuery.isLoading}
        isError={summaryQuery.isError}
        error={summaryQuery.error}
        data={summaryQuery.data}
      >
        {(summary) => (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <SummaryCard label="Market Value" value={formatCurrency(summary.total_market_value)} />
            <SummaryCard label="Remaining Cost Basis" value={formatCurrency(summary.remaining_cost_basis)} />
            <SummaryCard label="Total P&L" value={formatCurrency(summary.total_pnl)} sign={signOf(summary.total_pnl)} />
            <SummaryCard label="Holdings" value={String(summary.holdings_count)} />
          </div>
        )}
      </QueryState>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">Asset Allocation</h2>
          <QueryState
            isLoading={allocationQuery.isLoading}
            isError={allocationQuery.isError}
            error={allocationQuery.error}
            data={allocationQuery.data}
            isEmpty={(d) => d.entries.length === 0}
            emptyTitle="No holdings yet."
          >
            {(allocation) => <AllocationChart entries={allocation.entries} />}
          </QueryState>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">Concentration Risk</h2>
          <QueryState
            isLoading={riskQuery.isLoading}
            isError={riskQuery.isError}
            error={riskQuery.error}
            data={riskQuery.data}
            isEmpty={(d) => d.top_holdings.length === 0}
            emptyTitle="No holdings to assess yet."
          >
            {(risk) => (
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-slate-400">Largest single position</p>
                  <p className="text-lg font-semibold tabular-nums">
                    <Percent value={risk.max_single_position_weight} colorBySign={false} />
                  </p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium text-slate-500">Sector concentration</p>
                  <ul className="space-y-1">
                    {risk.sector_concentration.map((s) => (
                      <li key={s.sector ?? "unclassified"} className="flex items-center justify-between text-sm">
                        <span className="text-slate-600">{s.sector ?? "Unclassified"}</span>
                        <Percent value={s.weight} colorBySign={false} />
                      </li>
                    ))}
                  </ul>
                </div>
                <p className="text-xs text-slate-400">{risk.note}</p>
              </div>
            )}
          </QueryState>
        </section>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Holdings</h2>
          <QueryState
            isLoading={accountsQuery.isLoading}
            isError={accountsQuery.isError}
            error={accountsQuery.error}
            data={accountsQuery.data}
          >
            {(accounts) => (
              <select
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                value={accountId ?? ""}
                onChange={(e) => setAccountId(e.target.value ? Number(e.target.value) : undefined)}
              >
                <option value="">All accounts</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            )}
          </QueryState>
        </div>

        <QueryState
          isLoading={holdingsQuery.isLoading}
          isError={holdingsQuery.isError}
          error={holdingsQuery.error}
          data={holdingsQuery.data}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No holdings yet."
          emptyHint="Add your first transaction to start tracking a position."
        >
          {(holdings) => (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="py-2 pr-4">Ticker</th>
                    <th className="py-2 pr-4 text-right">Shares</th>
                    <th className="py-2 pr-4 text-right">Avg Cost</th>
                    <th className="py-2 pr-4 text-right">Cost Basis</th>
                    <th className="py-2 pr-4 text-right">Price</th>
                    <th className="py-2 pr-4 text-right">Market Value</th>
                    <th className="py-2 pr-4 text-right">Unrealized</th>
                    <th className="py-2 pr-4 text-right">Realized</th>
                    <th className="py-2 pr-4 text-right">Return</th>
                    <th className="py-2 text-right">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => (
                    <tr key={`${h.account_id}-${h.asset_id}`} className="border-b border-slate-100 last:border-0">
                      <td className="py-2 pr-4">
                        <div className="font-medium text-slate-900">{h.ticker}</div>
                        <div className="text-xs text-slate-400">{h.asset_name}</div>
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Shares value={h.remaining_shares} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={h.average_cost} decimals={2} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={h.remaining_cost_basis} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={h.latest_close} decimals={2} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={h.market_value} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={h.unrealized_pnl} colorBySign />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={h.realized_pnl} colorBySign />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Percent value={h.return_pct} />
                      </td>
                      <td className="py-2 text-right">
                        <Percent value={h.weight} colorBySign={false} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryState>
      </section>
    </div>
  );
}
