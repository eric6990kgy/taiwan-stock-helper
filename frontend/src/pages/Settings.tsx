import { DemoDataBadge } from "../components/Badges";
import { PrimaryButton } from "../components/form";
import { QueryState } from "../components/QueryState";
import { useAccounts } from "../features/transactions/hooks";
import { useUpdateMarketData } from "../features/marketData/hooks";
import { ApiRequestError } from "../services/api";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export function Settings() {
  const accountsQuery = useAccounts();
  const updateMarketData = useUpdateMarketData();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">App info and accounts. Nothing here talks to a broker or a bank.</p>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-900">Data Source</h2>
        <div className="flex items-start gap-3">
          <DemoDataBadge />
          <p className="text-sm text-slate-600">
            Assets start out as seeded demo data. Running "Update Market Data" below replaces a stock's data with
            real prices/fundamentals from FinMind and flips it out of demo status automatically — every row still
            carries its own source (MOCK or FINMIND), so nothing here is ever mistaken for a real-time quote.
          </p>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Update Market Data</h2>
          <PrimaryButton onClick={() => updateMarketData.mutate()} disabled={updateMarketData.isPending}>
            {updateMarketData.isPending ? "Updating…" : "Update Market Data"}
          </PrimaryButton>
        </div>
        <p className="mb-3 text-sm text-slate-500">
          Pulls fresh prices, fundamentals, dividends, and valuation ratios from FinMind for every stock/ETF asset.
          Manual only for now — there's no scheduled daily update yet.
        </p>

        {updateMarketData.isError && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {updateMarketData.error instanceof ApiRequestError
              ? updateMarketData.error.message
              : "Failed to update market data."}
          </p>
        )}

        {updateMarketData.isSuccess && (
          <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                  updateMarketData.data.status === "completed"
                    ? "bg-green-50 text-green-700"
                    : "bg-amber-50 text-amber-700"
                }`}
              >
                {updateMarketData.data.status === "completed" ? "Completed" : "Stopped — rate limited"}
              </span>
              <span className="text-slate-500">{updateMarketData.data.assets_processed} assets processed</span>
              <span className="text-slate-500">·</span>
              <span className="text-slate-500">
                Source: <span className="font-mono">{updateMarketData.data.source}</span>
              </span>
              {updateMarketData.data.latest_data_date && (
                <>
                  <span className="text-slate-500">·</span>
                  <span className="text-slate-500">As of: {updateMarketData.data.latest_data_date}</span>
                </>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <p className="mb-1 text-xs font-medium text-slate-500">
                  Succeeded ({updateMarketData.data.succeeded.length})
                </p>
                <p className="text-sm text-slate-700">{updateMarketData.data.succeeded.join(", ") || "—"}</p>
              </div>
              <div>
                <p className="mb-1 text-xs font-medium text-slate-500">Failed ({updateMarketData.data.failed.length})</p>
                {updateMarketData.data.failed.length === 0 ? (
                  <p className="text-sm text-slate-700">—</p>
                ) : (
                  <ul className="space-y-1 text-sm text-red-600">
                    {updateMarketData.data.failed.map((f) => (
                      <li key={f.ticker}>
                        <span className="font-medium">{f.ticker}</span>: {f.reason}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {updateMarketData.data.validation_warnings.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium text-slate-500">
                  Validation warnings ({updateMarketData.data.validation_warnings.length})
                </p>
                <ul className="space-y-1 text-sm text-amber-700">
                  {updateMarketData.data.validation_warnings.map((w, i) => (
                    <li key={i}>
                      <span className="font-medium">{w.ticker}</span>: {w.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Accounts</h2>
        <QueryState
          isLoading={accountsQuery.isLoading}
          isError={accountsQuery.isError}
          error={accountsQuery.error}
          data={accountsQuery.data}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No accounts yet."
        >
          {(accounts) => (
            <ul className="divide-y divide-slate-100">
              {accounts.map((a) => (
                <li key={a.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="font-medium text-slate-800">{a.name}</span>
                  <span className="text-xs text-slate-400">
                    {a.account_type} · {a.currency}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </QueryState>
        <p className="mt-3 text-xs text-slate-400">
          Adding/editing accounts from this screen isn't built yet — use the API directly (see the Swagger docs) if
          you need another account for now.
        </p>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-900">About</h2>
        <dl className="space-y-1 text-sm">
          <div className="flex justify-between">
            <dt className="text-slate-500">API endpoint</dt>
            <dd className="font-mono text-xs text-slate-600">{API_URL}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Version</dt>
            <dd className="text-slate-600">V1 (Phase 4 — Frontend Dashboard)</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
