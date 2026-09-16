import { QueryState } from "../components/QueryState";
import {
  useConfirmPendingChange,
  usePendingStrategyChanges,
  useRejectPendingChange,
  useStrategyVersions,
} from "../features/recommendations/hooks";
import { formatMoney } from "../utils/decimal";
import type { BacktestSummary, PendingStrategyChange, StrategyVersion } from "../types/api";

const STATUS_STYLES: Record<StrategyVersion["status"], string> = {
  ACTIVE: "bg-green-50 text-green-700 ring-green-200",
  SUPERSEDED: "bg-slate-100 text-slate-500 ring-slate-200",
  ROLLED_BACK: "bg-amber-50 text-amber-700 ring-amber-200",
};

/** The signal engine's tunable parameters, versioned and auditable
 * (個股訊號引擎規格書 Phase B). A small change (same parameter keys, only
 * values differ) auto-applies; a big one (a key added/removed) sits here
 * pending your explicit confirmation -- never silently promoted. */
export function Strategy() {
  const versionsQuery = useStrategyVersions();
  const pendingQuery = usePendingStrategyChanges("PENDING");
  const confirmChange = useConfirmPendingChange();
  const rejectChange = useRejectPendingChange();

  const activeVersion = versionsQuery.data?.find((v) => v.status === "ACTIVE");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Strategy</h1>
        <p className="text-sm text-slate-500">Versioned signal-engine parameters behind the Recommendations page.</p>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Active Version</h2>
        <QueryState
          isLoading={versionsQuery.isLoading}
          isError={versionsQuery.isError}
          error={versionsQuery.error}
          data={activeVersion}
        >
          {(version) => <VersionDetail version={version} />}
        </QueryState>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Pending Changes</h2>
        <QueryState
          isLoading={pendingQuery.isLoading}
          isError={pendingQuery.isError}
          error={pendingQuery.error}
          data={pendingQuery.data}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No changes awaiting confirmation."
        >
          {(pending) => (
            <div className="flex flex-col gap-3">
              {pending.map((change) => (
                <PendingChangeCard
                  key={change.id}
                  change={change}
                  onConfirm={() => confirmChange.mutate(change.id)}
                  onReject={() => rejectChange.mutate(change.id)}
                  isPending={confirmChange.isPending || rejectChange.isPending}
                />
              ))}
            </div>
          )}
        </QueryState>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Version History</h2>
        <QueryState
          isLoading={versionsQuery.isLoading}
          isError={versionsQuery.isError}
          error={versionsQuery.error}
          data={versionsQuery.data}
          isEmpty={(d) => d.length === 0}
        >
          {(versions) => (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="py-2 pr-4">Version</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4">Change Type</th>
                    <th className="py-2 pr-4">Reason</th>
                    <th className="py-2 pr-4">Hit Rate</th>
                    <th className="py-2">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((v) => (
                    <tr key={v.id} className="border-b border-slate-100 last:border-0">
                      <td className="py-2 pr-4 font-medium text-slate-900">v{v.version_number}</td>
                      <td className="py-2 pr-4">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${STATUS_STYLES[v.status]}`}>
                          {v.status}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-slate-600">{v.change_type}</td>
                      <td className="max-w-xs py-2 pr-4 text-slate-600">{v.reason ?? "—"}</td>
                      <td className="py-2 pr-4 text-slate-600">
                        {v.backtest_hit_rate !== null ? formatMoney(String(Number(v.backtest_hit_rate) * 100), 1) + "%" : "—"}
                      </td>
                      <td className="py-2 text-slate-500">{new Date(v.created_at).toLocaleDateString()}</td>
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

function VersionDetail({ version }: { version: StrategyVersion }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-lg font-semibold text-slate-900">v{version.version_number}</span>
        <span className="text-xs text-slate-400">{version.change_type}</span>
      </div>
      {version.reason && <p className="text-sm text-slate-600">{version.reason}</p>}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {Object.entries(version.rules).map(([key, value]) => (
          <div key={key}>
            <p className="text-xs text-slate-400">{key}</p>
            <p className="text-sm font-medium tabular-nums text-slate-800">{String(value)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function PendingChangeCard({
  change,
  onConfirm,
  onReject,
  isPending,
}: {
  change: PendingStrategyChange;
  onConfirm: () => void;
  onReject: () => void;
  isPending: boolean;
}) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4">
      <p className="text-sm text-slate-700">{change.reason}</p>
      <div className="mt-2 grid grid-cols-2 gap-4 text-xs sm:grid-cols-4">
        {Object.entries(change.proposed_rules).map(([key, value]) => (
          <div key={key}>
            <p className="text-slate-400">{key}</p>
            <p className="font-medium tabular-nums text-slate-700">{String(value)}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
        <BacktestSummaryLabel label="Before" summary={change.backtest_before} />
        <BacktestSummaryLabel label="After" summary={change.backtest_after} />
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button
          type="button"
          disabled={isPending}
          onClick={onReject}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
        >
          Reject
        </button>
        <button
          type="button"
          disabled={isPending}
          onClick={onConfirm}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          Confirm
        </button>
      </div>
    </div>
  );
}

function BacktestSummaryLabel({ label, summary }: { label: string; summary: BacktestSummary | null }) {
  if (!summary || summary.hit_rate === null) {
    return (
      <span>
        {label}: <span className="text-slate-400">insufficient sample</span>
      </span>
    );
  }
  return (
    <span>
      {label}: {formatMoney(String(Number(summary.hit_rate) * 100), 1)}% ({summary.hits}/{summary.n})
    </span>
  );
}
