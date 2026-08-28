import { useState } from "react";
import { Field, inputClass, PrimaryButton, SecondaryButton } from "../components/form";
import { Modal } from "../components/Modal";
import { QueryState } from "../components/QueryState";
import { useAssets } from "../features/transactions/hooks";
import {
  useCreateWatchlistEntry,
  useDeleteWatchlistEntry,
  useUpdateWatchlistEntry,
  useWatchlist,
} from "../features/watchlist/hooks";
import { ApiRequestError } from "../services/api";
import type { WatchlistStatus } from "../types/api";

const STATUSES: WatchlistStatus[] = ["WATCHING", "RESEARCHING", "CANDIDATE", "OWNED", "REJECTED"];

export function Watchlist() {
  const [statusFilter, setStatusFilter] = useState<WatchlistStatus | "">("");
  const [showAddModal, setShowAddModal] = useState(false);

  const watchlistQuery = useWatchlist(statusFilter || undefined);
  const updateEntry = useUpdateWatchlistEntry();
  const deleteEntry = useDeleteWatchlistEntry();

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Watchlist</h1>
          <p className="text-sm text-slate-500">Stocks you're watching, researching, or considering.</p>
        </div>
        <PrimaryButton onClick={() => setShowAddModal(true)}>Add to Watchlist</PrimaryButton>
      </div>

      <div className="flex gap-1">
        <FilterChip label="All" active={statusFilter === ""} onClick={() => setStatusFilter("")} />
        {STATUSES.map((s) => (
          <FilterChip key={s} label={s} active={statusFilter === s} onClick={() => setStatusFilter(s)} />
        ))}
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="py-2 pr-4">Ticker</th>
                    <th className="py-2 pr-4">Reason</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4">Review Date</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <tr key={entry.id} className="border-b border-slate-100 last:border-0">
                      <td className="py-2 pr-4">
                        <div className="font-medium text-slate-900">{entry.ticker}</div>
                        <div className="text-xs text-slate-400">{entry.asset_name}</div>
                      </td>
                      <td className="max-w-xs py-2 pr-4 text-slate-600">{entry.reason ?? "—"}</td>
                      <td className="py-2 pr-4">
                        <select
                          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
                          value={entry.status}
                          onChange={(e) => updateEntry.mutate({ id: entry.id, body: { status: e.target.value } })}
                        >
                          {STATUSES.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 pr-4 text-slate-500">{entry.review_date ?? "—"}</td>
                      <td className="py-2 text-right">
                        <button
                          type="button"
                          className="text-xs font-medium text-red-600 hover:underline"
                          onClick={() => {
                            if (confirm(`Remove ${entry.ticker} from the watchlist?`)) {
                              deleteEntry.mutate(entry.id);
                            }
                          }}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryState>
      </section>

      {showAddModal && <AddWatchlistModal onClose={() => setShowAddModal(false)} />}
    </div>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium ${
        active ? "bg-blue-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
      }`}
    >
      {label}
    </button>
  );
}

function AddWatchlistModal({ onClose }: { onClose: () => void }) {
  const assetsQuery = useAssets();
  const createEntry = useCreateWatchlistEntry();

  const [assetId, setAssetId] = useState("");
  const [status, setStatus] = useState<WatchlistStatus>("WATCHING");
  const [reason, setReason] = useState("");
  const [entryConsideration, setEntryConsideration] = useState("");
  const [reviewDate, setReviewDate] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!assetId) {
      setFormError("Pick a ticker.");
      return;
    }
    try {
      await createEntry.mutateAsync({
        asset_id: Number(assetId),
        status,
        reason: reason || undefined,
        entry_consideration: entryConsideration || undefined,
        review_date: reviewDate || undefined,
      });
      onClose();
    } catch (err) {
      setFormError(err instanceof ApiRequestError ? err.message : "Failed to add to watchlist.");
    }
  }

  return (
    <Modal title="Add to Watchlist" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        <QueryState isLoading={assetsQuery.isLoading} isError={assetsQuery.isError} error={assetsQuery.error} data={assetsQuery.data}>
          {(assets) => (
            <Field label="Ticker">
              <select className={inputClass} value={assetId} onChange={(e) => setAssetId(e.target.value)} required>
                <option value="">Select a ticker</option>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.ticker} — {a.name}
                  </option>
                ))}
              </select>
            </Field>
          )}
        </QueryState>

        <Field label="Status">
          <select className={inputClass} value={status} onChange={(e) => setStatus(e.target.value as WatchlistStatus)}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Watch Reason">
          <textarea className={`${inputClass} min-h-16`} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>

        <Field label="Entry Consideration">
          <input className={inputClass} value={entryConsideration} onChange={(e) => setEntryConsideration(e.target.value)} />
        </Field>

        <Field label="Review Date">
          <input type="date" className={inputClass} value={reviewDate} onChange={(e) => setReviewDate(e.target.value)} />
        </Field>

        {formError && <p className="text-sm text-red-600">{formError}</p>}

        <div className="mt-2 flex justify-end gap-2">
          <SecondaryButton type="button" onClick={onClose}>
            Cancel
          </SecondaryButton>
          <PrimaryButton type="submit" disabled={createEntry.isPending}>
            {createEntry.isPending ? "Saving…" : "Add"}
          </PrimaryButton>
        </div>
      </form>
    </Modal>
  );
}
