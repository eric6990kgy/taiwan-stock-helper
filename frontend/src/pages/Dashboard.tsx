import { DemoDataBadge, SnapshotBadge, WatchlistStatusBadge } from "../components/Badges";
import { AllocationChart } from "../components/AllocationChart";
import { Money, Percent, Shares } from "../components/Money";
import { QueryState } from "../components/QueryState";
import { SummaryCard } from "../components/SummaryCard";
import { useAllocation, useHoldings, usePerformance, usePortfolioSummary } from "../features/portfolio/hooks";
import { useWatchlist } from "../features/watchlist/hooks";
import { formatCurrency, formatPercent, signOf } from "../utils/decimal";

export function Dashboard() {
  const summaryQuery = usePortfolioSummary();
  const holdingsQuery = useHoldings();
  const allocationQuery = useAllocation();
  const watchlistQuery = useWatchlist();
  const performanceQuery = usePerformance();

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">Where your money is, and how it's doing today.</p>
        </div>
        <DemoDataBadge />
      </div>

      <QueryState
        isLoading={summaryQuery.isLoading}
        isError={summaryQuery.isError}
        error={summaryQuery.error}
        data={summaryQuery.data}
      >
        {(summary) => (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
            <SummaryCard label="Total Market Value" value={formatCurrency(summary.total_market_value)} />
            <SummaryCard label="Remaining Cost Basis" value={formatCurrency(summary.remaining_cost_basis)} />
            <SummaryCard
              label="Unrealized P&L"
              value={formatCurrency(summary.unrealized_pnl)}
              sign={signOf(summary.unrealized_pnl)}
            />
            <SummaryCard
              label="Realized P&L"
              value={formatCurrency(summary.realized_pnl)}
              sign={signOf(summary.realized_pnl)}
            />
            <SummaryCard
              label="Total Return %"
              value={formatPercent(summary.total_return_pct)}
              sign={signOf(summary.total_return_pct)}
            />
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
            emptyHint="Add a transaction to see your allocation."
          >
            {(allocation) => <AllocationChart entries={allocation.entries} />}
          </QueryState>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-900">Performance</h2>
            <SnapshotBadge />
          </div>
          <QueryState
            isLoading={performanceQuery.isLoading}
            isError={performanceQuery.isError}
            error={performanceQuery.error}
            data={performanceQuery.data}
          >
            {(perf) => (
              <div className="space-y-3">
                <p className="text-xs text-slate-400">{perf.note}</p>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-xs text-slate-400">Market Value</dt>
                    <dd className="tabular-nums font-medium">
                      <Money value={perf.total_market_value} />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-400">Total P&amp;L</dt>
                    <dd className="tabular-nums font-medium">
                      <Money value={perf.total_pnl} colorBySign />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-400">Realized</dt>
                    <dd className="tabular-nums font-medium">
                      <Money value={perf.realized_pnl} colorBySign />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-400">Unrealized</dt>
                    <dd className="tabular-nums font-medium">
                      <Money value={perf.unrealized_pnl} colorBySign />
                    </dd>
                  </div>
                </dl>
              </div>
            )}
          </QueryState>
        </section>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Holdings</h2>
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
                    <th className="py-2 pr-4 text-right">Price</th>
                    <th className="py-2 pr-4 text-right">Market Value</th>
                    <th className="py-2 pr-4 text-right">Unrealized P&amp;L</th>
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
                        <Money value={h.latest_close} decimals={2} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={h.market_value} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={h.unrealized_pnl} colorBySign />
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Watchlist</h2>
          <QueryState
            isLoading={watchlistQuery.isLoading}
            isError={watchlistQuery.isError}
            error={watchlistQuery.error}
            data={watchlistQuery.data}
            isEmpty={(d) => d.length === 0}
            emptyTitle="Your watchlist is empty."
            emptyHint="Add a stock to research."
          >
            {(entries) => (
              <ul className="divide-y divide-slate-100">
                {entries.map((entry) => (
                  <li key={entry.id} className="flex items-center justify-between py-2">
                    <div>
                      <p className="text-sm font-medium text-slate-900">{entry.ticker}</p>
                      <p className="text-xs text-slate-400">{entry.asset_name}</p>
                    </div>
                    <WatchlistStatusBadge status={entry.status} />
                  </li>
                ))}
              </ul>
            )}
          </QueryState>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Alerts</h2>
          <div className="flex flex-col items-center justify-center gap-1 py-8 text-center">
            <p className="text-sm text-slate-500">No alerts configured yet.</p>
            <p className="text-xs text-slate-400">
              Thesis review reminders, price movement, and earnings alerts are on the roadmap (not yet implemented).
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
