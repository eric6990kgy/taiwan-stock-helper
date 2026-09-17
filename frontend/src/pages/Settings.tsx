import { useState } from "react";
import { AddAssetModal } from "../components/AddAssetModal";
import { DemoDataBadge } from "../components/Badges";
import { Modal } from "../components/Modal";
import { Field, PrimaryButton, SecondaryButton, inputClass } from "../components/form";
import { QueryState } from "../components/QueryState";
import {
  useAccounts,
  useAssets,
  useCreateAccount,
  useDeleteAccount,
  useImportTransactions,
  useUpdateAccount,
} from "../features/transactions/hooks";
import { useUpdateMarketData } from "../features/marketData/hooks";
import { ApiRequestError, exportUrls } from "../services/api";
import type { Account, AccountType } from "../types/api";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const ACCOUNT_TYPES: AccountType[] = ["BROKERAGE", "BANK", "GLOBAL_INVEST", "CASH"];

export function Settings() {
  const accountsQuery = useAccounts();
  const assetsQuery = useAssets();
  const updateMarketData = useUpdateMarketData();

  const [accountModal, setAccountModal] = useState<{ account?: Account } | null>(null);
  const [showAddAsset, setShowAddAsset] = useState(false);
  const [deleteErrorFor, setDeleteErrorFor] = useState<{ id: number; message: string } | null>(null);
  const deleteAccount = useDeleteAccount();

  function handleDeleteAccount(account: Account) {
    if (!confirm(`Delete account "${account.name}"? This cannot be undone.`)) return;
    setDeleteErrorFor(null);
    deleteAccount.mutate(account.id, {
      onError: (err) =>
        setDeleteErrorFor({
          id: account.id,
          message: err instanceof ApiRequestError ? err.message : "Failed to delete account.",
        }),
    });
  }

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
          Manual only for now, or once daily via the Windows Task Scheduler job — see README.
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
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Accounts</h2>
          <PrimaryButton onClick={() => setAccountModal({})}>Add Account</PrimaryButton>
        </div>
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
                <li key={a.id} className="flex flex-col gap-1 py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-800">{a.name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-400">
                        {a.account_type} · {a.currency}
                      </span>
                      <button
                        type="button"
                        className="text-xs font-medium text-blue-600 hover:underline"
                        onClick={() => setAccountModal({ account: a })}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="text-xs font-medium text-red-600 hover:underline"
                        onClick={() => handleDeleteAccount(a)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  {deleteErrorFor?.id === a.id && <p className="text-xs text-red-600">{deleteErrorFor.message}</p>}
                </li>
              ))}
            </ul>
          )}
        </QueryState>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Assets</h2>
          <PrimaryButton onClick={() => setShowAddAsset(true)}>Add Asset</PrimaryButton>
        </div>
        <QueryState
          isLoading={assetsQuery.isLoading}
          isError={assetsQuery.isError}
          error={assetsQuery.error}
          data={assetsQuery.data}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No assets yet."
        >
          {(assets) => (
            <ul className="max-h-64 divide-y divide-slate-100 overflow-y-auto">
              {assets.map((a) => (
                <li key={a.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="font-medium text-slate-800">
                    {a.ticker} — {a.name}
                  </span>
                  <span className="flex items-center gap-2 text-xs text-slate-400">
                    {a.asset_type}
                    {a.is_demo_data && <DemoDataBadge />}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </QueryState>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-900">Data Import / Export</h2>
        <ImportExportSection />
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
            <dd className="text-slate-600">V1 (Phase 9 — Asset Management UX)</dd>
          </div>
        </dl>
      </section>

      {accountModal && (
        <AccountModal account={accountModal.account} onClose={() => setAccountModal(null)} />
      )}
      {showAddAsset && <AddAssetModal onClose={() => setShowAddAsset(false)} />}
    </div>
  );
}

function AccountModal({ account, onClose }: { account?: Account; onClose: () => void }) {
  const createAccount = useCreateAccount();
  const updateAccount = useUpdateAccount();
  const isEditing = account != null;

  const [name, setName] = useState(account?.name ?? "");
  const [accountType, setAccountType] = useState<AccountType>(account?.account_type ?? "BROKERAGE");
  const [currency, setCurrency] = useState(account?.currency ?? "TWD");
  const [formError, setFormError] = useState<string | null>(null);

  const isPending = isEditing ? updateAccount.isPending : createAccount.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!name.trim()) {
      setFormError("Name is required.");
      return;
    }
    try {
      if (isEditing) {
        await updateAccount.mutateAsync({ id: account.id, body: { name: name.trim(), account_type: accountType } });
      } else {
        await createAccount.mutateAsync({ name: name.trim(), account_type: accountType, currency: currency.trim() });
      }
      onClose();
    } catch (err) {
      setFormError(err instanceof ApiRequestError ? err.message : "Failed to save account.");
    }
  }

  return (
    <Modal title={isEditing ? "Edit Account" : "Add Account"} onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        <Field label="Name">
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>

        <Field label="Account Type">
          <select className={inputClass} value={accountType} onChange={(e) => setAccountType(e.target.value as AccountType)}>
            {ACCOUNT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>

        {!isEditing && (
          <Field label="Currency">
            <input className={inputClass} value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </Field>
        )}

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

function ImportExportSection() {
  const importTransactions = useImportTransactions();
  const [file, setFile] = useState<File | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!file) {
      setFormError("Choose a CSV file first.");
      return;
    }
    try {
      await importTransactions.mutateAsync(file);
      setFile(null);
    } catch (err) {
      setFormError(err instanceof ApiRequestError ? err.message : "Import failed.");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="mb-2 text-sm font-medium text-slate-700">Export</p>
        <div className="flex flex-wrap gap-2">
          <a href={exportUrls.transactions} download className="text-sm font-medium text-blue-600 hover:underline">
            Transactions.csv
          </a>
          <span className="text-slate-300">·</span>
          <a href={exportUrls.holdings} download className="text-sm font-medium text-blue-600 hover:underline">
            Holdings.csv
          </a>
          <span className="text-slate-300">·</span>
          <a href={exportUrls.portfolioSnapshot} download className="text-sm font-medium text-blue-600 hover:underline">
            Portfolio-Snapshot.csv
          </a>
        </div>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium text-slate-700">Import Transactions</p>
        <p className="mb-2 text-xs text-slate-500">
          CSV columns required (in any order):{" "}
          <span className="font-mono">account_name,ticker,date,type,quantity,price,fee,tax,currency,note</span>
        </p>
        <form className="flex flex-wrap items-center gap-2" onSubmit={handleImport}>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-slate-600"
          />
          <PrimaryButton type="submit" disabled={importTransactions.isPending}>
            {importTransactions.isPending ? "Importing…" : "Import"}
          </PrimaryButton>
        </form>

        {formError && <p className="mt-2 text-sm text-red-600">{formError}</p>}

        {importTransactions.isSuccess && (
          <div className="mt-3 space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
            <p className="font-medium text-green-700">Imported {importTransactions.data.imported} row(s).</p>

            {importTransactions.data.needs_review_tickers.length > 0 && (
              <div>
                <p className="text-xs font-medium text-amber-700">
                  Auto-created and flagged for review — please check these tickers:
                </p>
                <p className="text-sm text-slate-700">{importTransactions.data.needs_review_tickers.join(", ")}</p>
              </div>
            )}

            {importTransactions.data.skipped.length > 0 && (
              <div>
                <p className="text-xs font-medium text-red-600">Skipped ({importTransactions.data.skipped.length}):</p>
                <ul className="space-y-1 text-red-600">
                  {importTransactions.data.skipped.map((s) => (
                    <li key={s.row}>
                      Row {s.row}: {s.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
