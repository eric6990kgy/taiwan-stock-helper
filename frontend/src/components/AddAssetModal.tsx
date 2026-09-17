import { useEffect, useState } from "react";
import { useAssetLookup, useQuickCreateAsset } from "../features/transactions/hooks";
import { ApiRequestError } from "../services/api";
import type { Asset } from "../types/api";
import { Field, PrimaryButton, SecondaryButton, inputClass } from "./form";
import { Modal } from "./Modal";

const DEBOUNCE_MS = 500;

interface AddAssetModalProps {
  onClose: () => void;
  /** Called with the newly-created asset in addition to onClose, so a
   * caller (e.g. the Add Transaction / Add to Watchlist modal) can
   * pre-select it without the user having to re-open its own picker. */
  onCreated?: (asset: Asset) => void;
}

/** Phase 11: "just type the ticker" -- name/market/sector are looked up
 * from FinMind and previewed before the user commits, instead of asking
 * them to fill in seven fields by hand. */
export function AddAssetModal({ onClose, onCreated }: AddAssetModalProps) {
  const [ticker, setTicker] = useState("");
  const [debouncedTicker, setDebouncedTicker] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const quickCreate = useQuickCreateAsset();

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedTicker(ticker.trim().toUpperCase()), DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [ticker]);

  const lookup = useAssetLookup(debouncedTicker, debouncedTicker.length > 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!lookup.data) {
      setFormError("請先輸入有效的股票代碼。");
      return;
    }
    try {
      const asset = await quickCreate.mutateAsync(lookup.data.ticker);
      onCreated?.(asset);
      onClose();
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 409) {
        setFormError("此股票代號已存在 (ticker already exists).");
      } else {
        setFormError(err instanceof ApiRequestError ? err.message : "Failed to add asset.");
      }
    }
  }

  return (
    <Modal title="Add Asset" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        <Field label="股票代碼">
          <input
            className={inputClass}
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="例如 2330"
            autoFocus
            required
          />
        </Field>

        {debouncedTicker && lookup.isLoading && <p className="text-sm text-slate-400">查詢中…</p>}
        {debouncedTicker && lookup.isError && <p className="text-sm text-red-600">查無此股票代碼。</p>}
        {lookup.data && (
          <p className="text-sm text-green-600">
            ✓ 已自動查到：{lookup.data.name}（{lookup.data.market ?? "—"}）
          </p>
        )}

        {formError && <p className="text-sm text-red-600">{formError}</p>}

        <div className="mt-2 flex justify-end gap-2">
          <SecondaryButton type="button" onClick={onClose}>
            Cancel
          </SecondaryButton>
          <PrimaryButton type="submit" disabled={!lookup.data || quickCreate.isPending}>
            {quickCreate.isPending ? "Saving…" : "Add"}
          </PrimaryButton>
        </div>
      </form>
    </Modal>
  );
}
