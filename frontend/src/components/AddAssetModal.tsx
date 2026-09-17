import { useState } from "react";
import { useCreateAsset } from "../features/transactions/hooks";
import { ApiRequestError } from "../services/api";
import type { Asset, AssetType, ValuationMethod } from "../types/api";
import { Field, PrimaryButton, SecondaryButton, inputClass } from "./form";
import { Modal } from "./Modal";

const ASSET_TYPES: AssetType[] = ["STOCK", "ETF", "CASH", "FUND"];
const VALUATION_METHODS: ValuationMethod[] = ["TRANSACTION_BASED", "MANUAL_MARKET_VALUE"];

interface AddAssetModalProps {
  onClose: () => void;
  /** Called with the newly-created asset in addition to onClose, so a
   * caller (e.g. the Add Transaction / Add to Watchlist modal) can
   * pre-select it without the user having to re-open its own picker. */
  onCreated?: (asset: Asset) => void;
}

export function AddAssetModal({ onClose, onCreated }: AddAssetModalProps) {
  const createAsset = useCreateAsset();

  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState<AssetType>("STOCK");
  const [market, setMarket] = useState("");
  const [currency, setCurrency] = useState("TWD");
  const [sector, setSector] = useState("");
  const [industry, setIndustry] = useState("");
  const [valuationMethod, setValuationMethod] = useState<ValuationMethod>("TRANSACTION_BASED");
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!ticker.trim() || !name.trim()) {
      setFormError("Ticker and name are required.");
      return;
    }
    try {
      const asset = await createAsset.mutateAsync({
        ticker: ticker.trim(),
        name: name.trim(),
        asset_type: assetType,
        market: market.trim() || undefined,
        currency: currency.trim() || undefined,
        sector: sector.trim() || undefined,
        industry: industry.trim() || undefined,
        valuation_method: valuationMethod,
      });
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
        <Field label="Ticker">
          <input className={inputClass} value={ticker} onChange={(e) => setTicker(e.target.value)} required />
        </Field>

        <Field label="Name">
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>

        <Field label="Asset Type">
          <select className={inputClass} value={assetType} onChange={(e) => setAssetType(e.target.value as AssetType)}>
            {ASSET_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Market">
          <input className={inputClass} placeholder="TWSE / TPEx" value={market} onChange={(e) => setMarket(e.target.value)} />
        </Field>

        <Field label="Currency">
          <input className={inputClass} value={currency} onChange={(e) => setCurrency(e.target.value)} />
        </Field>

        <Field label="Sector">
          <input className={inputClass} value={sector} onChange={(e) => setSector(e.target.value)} />
        </Field>

        <Field label="Industry">
          <input className={inputClass} value={industry} onChange={(e) => setIndustry(e.target.value)} />
        </Field>

        <Field label="Valuation Method">
          <select
            className={inputClass}
            value={valuationMethod}
            onChange={(e) => setValuationMethod(e.target.value as ValuationMethod)}
          >
            {VALUATION_METHODS.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </Field>

        {formError && <p className="text-sm text-red-600">{formError}</p>}

        <div className="mt-2 flex justify-end gap-2">
          <SecondaryButton type="button" onClick={onClose}>
            Cancel
          </SecondaryButton>
          <PrimaryButton type="submit" disabled={createAsset.isPending}>
            {createAsset.isPending ? "Saving…" : "Add"}
          </PrimaryButton>
        </div>
      </form>
    </Modal>
  );
}
