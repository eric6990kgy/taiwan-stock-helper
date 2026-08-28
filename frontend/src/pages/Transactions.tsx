import { useState } from "react";
import { Field, inputClass, PrimaryButton, SecondaryButton } from "../components/form";
import { Modal } from "../components/Modal";
import { Money, Shares } from "../components/Money";
import { QueryState } from "../components/QueryState";
import { ApiRequestError } from "../services/api";
import { useAccounts, useAssets, useCreateTransaction, useDeleteTransaction, useTransactions } from "../features/transactions/hooks";
import type { TransactionType } from "../types/api";

const TRANSACTION_TYPES: TransactionType[] = ["BUY", "SELL", "DIVIDEND", "FEE", "CASH_DEPOSIT", "CASH_WITHDRAWAL"];

export function Transactions() {
  const [accountFilter, setAccountFilter] = useState<number | undefined>(undefined);
  const [showAddModal, setShowAddModal] = useState(false);

  const accountsQuery = useAccounts();
  const assetsQuery = useAssets();
  const transactionsQuery = useTransactions({ account_id: accountFilter });
  const deleteTransaction = useDeleteTransaction();

  const accountsById = new Map((accountsQuery.data ?? []).map((a) => [a.id, a]));
  const assetsById = new Map((assetsQuery.data ?? []).map((a) => [a.id, a]));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Transactions</h1>
          <p className="text-sm text-slate-500">Every buy, sell, dividend, and cash movement — the source of truth.</p>
        </div>
        <PrimaryButton onClick={() => setShowAddModal(true)}>Add Transaction</PrimaryButton>
      </div>

      <QueryState
        isLoading={accountsQuery.isLoading}
        isError={accountsQuery.isError}
        error={accountsQuery.error}
        data={accountsQuery.data}
      >
        {(accounts) => (
          <select
            className={`${inputClass} w-56`}
            value={accountFilter ?? ""}
            onChange={(e) => setAccountFilter(e.target.value ? Number(e.target.value) : undefined)}
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

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <QueryState
          isLoading={transactionsQuery.isLoading}
          isError={transactionsQuery.isError}
          error={transactionsQuery.error}
          data={transactionsQuery.data}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No transactions yet."
          emptyHint="Add your first transaction to start tracking a position."
        >
          {(transactions) => (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="py-2 pr-4">Date</th>
                    <th className="py-2 pr-4">Account</th>
                    <th className="py-2 pr-4">Ticker</th>
                    <th className="py-2 pr-4">Type</th>
                    <th className="py-2 pr-4 text-right">Quantity</th>
                    <th className="py-2 pr-4 text-right">Price</th>
                    <th className="py-2 pr-4 text-right">Fee</th>
                    <th className="py-2 pr-4 text-right">Tax</th>
                    <th className="py-2 pr-4">Note</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id} className="border-b border-slate-100 last:border-0">
                      <td className="py-2 pr-4 text-slate-600">{t.date}</td>
                      <td className="py-2 pr-4 text-slate-600">{accountsById.get(t.account_id)?.name ?? t.account_id}</td>
                      <td className="py-2 pr-4 font-medium text-slate-900">{assetsById.get(t.asset_id)?.ticker ?? t.asset_id}</td>
                      <td className="py-2 pr-4">
                        <TypeBadge type={t.type} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Shares value={t.quantity} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={t.price} decimals={2} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={t.fee} decimals={2} />
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <Money value={t.tax} decimals={2} />
                      </td>
                      <td className="py-2 pr-4 text-slate-400">{t.note ?? ""}</td>
                      <td className="py-2 text-right">
                        <button
                          type="button"
                          className="text-xs font-medium text-red-600 hover:underline disabled:opacity-40"
                          disabled={deleteTransaction.isPending}
                          onClick={() => {
                            if (confirm(`Delete this ${t.type} transaction on ${t.date}?`)) {
                              deleteTransaction.mutate(t.id);
                            }
                          }}
                        >
                          Delete
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

      {showAddModal && <AddTransactionModal onClose={() => setShowAddModal(false)} />}
    </div>
  );
}

function TypeBadge({ type }: { type: TransactionType }) {
  const positive = type === "BUY" || type === "DIVIDEND" || type === "CASH_DEPOSIT";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${
        positive ? "bg-green-50 text-green-700 ring-green-200" : "bg-slate-100 text-slate-600 ring-slate-200"
      }`}
    >
      {type}
    </span>
  );
}

function AddTransactionModal({ onClose }: { onClose: () => void }) {
  const accountsQuery = useAccounts();
  const assetsQuery = useAssets();
  const createTransaction = useCreateTransaction();

  const [accountId, setAccountId] = useState("");
  const [assetId, setAssetId] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [type, setType] = useState<TransactionType>("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [fee, setFee] = useState("0");
  const [tax, setTax] = useState("0");
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!accountId || !assetId || !quantity || !price) {
      setFormError("Account, asset, quantity, and price are required.");
      return;
    }
    try {
      await createTransaction.mutateAsync({
        account_id: Number(accountId),
        asset_id: Number(assetId),
        date,
        type,
        quantity,
        price,
        fee,
        tax,
        currency: "TWD",
        note: note || undefined,
      });
      onClose();
    } catch (err) {
      setFormError(err instanceof ApiRequestError ? err.message : "Failed to create transaction.");
    }
  }

  return (
    <Modal title="Add Transaction" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        <QueryState isLoading={accountsQuery.isLoading} isError={accountsQuery.isError} error={accountsQuery.error} data={accountsQuery.data}>
          {(accounts) => (
            <Field label="Account">
              <select className={inputClass} value={accountId} onChange={(e) => setAccountId(e.target.value)} required>
                <option value="">Select an account</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </Field>
          )}
        </QueryState>

        <QueryState isLoading={assetsQuery.isLoading} isError={assetsQuery.isError} error={assetsQuery.error} data={assetsQuery.data}>
          {(assets) => (
            <Field label="Asset">
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

        <div className="grid grid-cols-2 gap-3">
          <Field label="Type">
            <select className={inputClass} value={type} onChange={(e) => setType(e.target.value as TransactionType)}>
              {TRANSACTION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Date">
            <input type="date" className={inputClass} value={date} onChange={(e) => setDate(e.target.value)} required />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Quantity">
            <input
              type="number"
              step="any"
              min="0"
              className={inputClass}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
          </Field>
          <Field label="Price (TWD)">
            <input
              type="number"
              step="any"
              min="0"
              className={inputClass}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              required
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Fee">
            <input type="number" step="any" min="0" className={inputClass} value={fee} onChange={(e) => setFee(e.target.value)} />
          </Field>
          <Field label="Tax">
            <input type="number" step="any" min="0" className={inputClass} value={tax} onChange={(e) => setTax(e.target.value)} />
          </Field>
        </div>

        <Field label="Note (optional)">
          <input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>

        {formError && <p className="text-sm text-red-600">{formError}</p>}

        <div className="mt-2 flex justify-end gap-2">
          <SecondaryButton type="button" onClick={onClose}>
            Cancel
          </SecondaryButton>
          <PrimaryButton type="submit" disabled={createTransaction.isPending}>
            {createTransaction.isPending ? "Saving…" : "Save Transaction"}
          </PrimaryButton>
        </div>
      </form>
    </Modal>
  );
}
