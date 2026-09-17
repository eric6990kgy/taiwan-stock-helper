import { useState } from "react";
import { JOURNAL_CATEGORY_LABELS, JournalCategoryBadge } from "../components/Badges";
import { Field, PrimaryButton, SecondaryButton, inputClass } from "../components/form";
import { Modal } from "../components/Modal";
import { QueryState } from "../components/QueryState";
import { useAssets } from "../features/transactions/hooks";
import { useCreateJournalEntry, useDeleteJournalEntry, useJournalEntries, useUpdateJournalEntry } from "../features/journal/hooks";
import { ApiRequestError } from "../services/api";
import type { JournalCategory, JournalEntry } from "../types/api";

const JOURNAL_CATEGORIES = Object.keys(JOURNAL_CATEGORY_LABELS) as JournalCategory[];

/** A dated, freeform note (投資日誌, Phase 10) -- append-only history, not
 * the single "what I currently believe" thesis card on the Research page.
 * Entries can stand alone or be tied to a specific ticker. `category` is a
 * fixed tag (requested so the log stays manageable/filterable as it grows,
 * not just a wall of free text). */
export function Journal() {
  const [assetFilter, setAssetFilter] = useState<number | undefined>(undefined);
  const [categoryFilter, setCategoryFilter] = useState<JournalCategory | undefined>(undefined);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<JournalEntry | null>(null);
  const [deleteErrorFor, setDeleteErrorFor] = useState<{ id: number; message: string } | null>(null);

  const assetsQuery = useAssets();
  const entriesQuery = useJournalEntries({ asset_id: assetFilter, category: categoryFilter });
  const deleteEntry = useDeleteJournalEntry();

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Journal</h1>
          <p className="text-sm text-slate-500">Your own dated notes -- general, or tied to a specific stock.</p>
        </div>
        <PrimaryButton onClick={() => setShowAddModal(true)}>Add Entry</PrimaryButton>
      </div>

      <div className="flex flex-wrap gap-3">
        <QueryState isLoading={assetsQuery.isLoading} isError={assetsQuery.isError} error={assetsQuery.error} data={assetsQuery.data}>
          {(assets) => (
            <select
              className={`${inputClass} w-56`}
              value={assetFilter ?? ""}
              onChange={(e) => setAssetFilter(e.target.value ? Number(e.target.value) : undefined)}
            >
              <option value="">All tickers</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.ticker} — {a.name}
                </option>
              ))}
            </select>
          )}
        </QueryState>

        <select
          className={`${inputClass} w-40`}
          value={categoryFilter ?? ""}
          onChange={(e) => setCategoryFilter((e.target.value as JournalCategory) || undefined)}
        >
          <option value="">All categories</option>
          {JOURNAL_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {JOURNAL_CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <QueryState
          isLoading={entriesQuery.isLoading}
          isError={entriesQuery.isError}
          error={entriesQuery.error}
          data={entriesQuery.data}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No journal entries yet."
          emptyHint="Add your first note above."
        >
          {(entries) => (
            <div className="flex flex-col divide-y divide-slate-100">
              {entries.map((entry) => (
                <div key={entry.id} className="flex flex-col gap-1 py-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-900">{entry.entry_date}</span>
                      <JournalCategoryBadge category={entry.category} />
                      {entry.ticker && <span className="text-xs text-slate-400">{entry.ticker} — {entry.asset_name}</span>}
                    </div>
                    <div className="flex items-center gap-3">
                      <button type="button" className="text-xs font-medium text-blue-600 hover:underline" onClick={() => setEditingEntry(entry)}>
                        Edit
                      </button>
                      <button
                        type="button"
                        className="text-xs font-medium text-red-600 hover:underline"
                        onClick={() => {
                          if (confirm("Delete this journal entry? This cannot be undone.")) {
                            setDeleteErrorFor(null);
                            deleteEntry.mutate(entry.id, {
                              onError: (err) =>
                                setDeleteErrorFor({
                                  id: entry.id,
                                  message: err instanceof ApiRequestError ? err.message : "Failed to delete entry.",
                                }),
                            });
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-slate-700">{entry.body}</p>
                  {deleteErrorFor?.id === entry.id && <p className="text-xs text-red-600">{deleteErrorFor.message}</p>}
                </div>
              ))}
            </div>
          )}
        </QueryState>
      </section>

      {showAddModal && <JournalEntryModal onClose={() => setShowAddModal(false)} />}
      {editingEntry && <JournalEntryModal entry={editingEntry} onClose={() => setEditingEntry(null)} />}
    </div>
  );
}

function JournalEntryModal({ entry, onClose }: { entry?: JournalEntry; onClose: () => void }) {
  const assetsQuery = useAssets();
  const createEntry = useCreateJournalEntry();
  const updateEntry = useUpdateJournalEntry();
  const isEditing = entry != null;

  const [entryDate, setEntryDate] = useState(entry?.entry_date ?? new Date().toISOString().slice(0, 10));
  const [category, setCategory] = useState<JournalCategory>(entry?.category ?? "OBSERVATION");
  const [assetId, setAssetId] = useState(entry?.asset_id ? String(entry.asset_id) : "");
  const [body, setBody] = useState(entry?.body ?? "");
  const [formError, setFormError] = useState<string | null>(null);

  const isPending = isEditing ? updateEntry.isPending : createEntry.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!body.trim()) {
      setFormError("Write something first.");
      return;
    }
    try {
      if (isEditing) {
        await updateEntry.mutateAsync({ id: entry.id, body: { entry_date: entryDate, category, body: body.trim() } });
      } else {
        await createEntry.mutateAsync({
          entry_date: entryDate,
          category,
          asset_id: assetId ? Number(assetId) : undefined,
          body: body.trim(),
        });
      }
      onClose();
    } catch (err) {
      setFormError(err instanceof ApiRequestError ? err.message : "Failed to save entry.");
    }
  }

  return (
    <Modal title={isEditing ? "Edit Entry" : "Add Entry"} onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Date">
            <input type="date" className={inputClass} value={entryDate} onChange={(e) => setEntryDate(e.target.value)} required />
          </Field>

          <Field label="Category">
            <select className={inputClass} value={category} onChange={(e) => setCategory(e.target.value as JournalCategory)}>
              {JOURNAL_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {JOURNAL_CATEGORY_LABELS[c]}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {!isEditing && (
          <QueryState isLoading={assetsQuery.isLoading} isError={assetsQuery.isError} error={assetsQuery.error} data={assetsQuery.data}>
            {(assets) => (
              <Field label="Ticker (optional)">
                <select className={inputClass} value={assetId} onChange={(e) => setAssetId(e.target.value)}>
                  <option value="">General note</option>
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.ticker} — {a.name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
          </QueryState>
        )}

        <Field label="Note">
          <textarea className={`${inputClass} min-h-32`} value={body} onChange={(e) => setBody(e.target.value)} />
        </Field>

        {formError && <p className="text-sm text-red-600">{formError}</p>}

        <div className="mt-2 flex justify-end gap-2">
          <SecondaryButton type="button" onClick={onClose}>
            Cancel
          </SecondaryButton>
          <PrimaryButton type="submit" disabled={isPending}>
            {isPending ? "Saving…" : isEditing ? "Save" : "Add"}
          </PrimaryButton>
        </div>
      </form>
    </Modal>
  );
}
