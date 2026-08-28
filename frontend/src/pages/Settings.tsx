import { DemoDataBadge } from "../components/Badges";
import { QueryState } from "../components/QueryState";
import { useAccounts } from "../features/transactions/hooks";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export function Settings() {
  const accountsQuery = useAccounts();

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
            All prices and fundamentals in this app are seeded demo data (V1 has no live market data connection).
            Every asset and price row is explicitly flagged so nothing here is mistaken for a real-time quote.
          </p>
        </div>
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
