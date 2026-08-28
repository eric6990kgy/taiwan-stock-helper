import { useEffect, useState } from "react";
import { DemoDataBadge, ThesisStatusBadge } from "../components/Badges";
import { Field, inputClass, PrimaryButton, SecondaryButton } from "../components/form";
import { Money, Percent } from "../components/Money";
import { PriceChart } from "../components/PriceChart";
import { QueryState } from "../components/QueryState";
import { useAssets } from "../features/transactions/hooks";
import { usePrices, useResearchPage, useUpsertThesis } from "../features/research/hooks";
import { ApiRequestError } from "../services/api";
import type { ThesisStatus } from "../types/api";

const RANGES = ["1M", "3M", "6M", "1Y", "3Y", "5Y"] as const;

export function Research() {
  const assetsQuery = useAssets();
  const [ticker, setTicker] = useState<string | null>(null);
  const [range, setRange] = useState<(typeof RANGES)[number]>("1Y");

  useEffect(() => {
    if (!ticker && assetsQuery.data && assetsQuery.data.length > 0) {
      const firstStock = assetsQuery.data.find((a) => a.asset_type === "STOCK") ?? assetsQuery.data[0];
      setTicker(firstStock.ticker);
    }
  }, [ticker, assetsQuery.data]);

  const researchQuery = useResearchPage(ticker);
  const pricesQuery = usePrices(ticker, range);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Research</h1>
          <p className="text-sm text-slate-500">Company profile, price history, fundamentals, and your thesis.</p>
        </div>
        <QueryState isLoading={assetsQuery.isLoading} isError={assetsQuery.isError} error={assetsQuery.error} data={assetsQuery.data}>
          {(assets) => (
            <select className={`${inputClass} w-64`} value={ticker ?? ""} onChange={(e) => setTicker(e.target.value)}>
              {assets.map((a) => (
                <option key={a.id} value={a.ticker}>
                  {a.ticker} — {a.name}
                </option>
              ))}
            </select>
          )}
        </QueryState>
      </div>

      <QueryState
        isLoading={researchQuery.isLoading}
        isError={researchQuery.isError}
        error={researchQuery.error}
        data={researchQuery.data}
      >
        {(page) => (
          <>
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-slate-900">
                      {page.name} <span className="text-slate-400">({page.ticker})</span>
                    </h2>
                    {page.is_demo_data && <DemoDataBadge />}
                  </div>
                  <p className="text-sm text-slate-500">
                    {[page.market, page.sector, page.industry].filter(Boolean).join(" · ") || "No profile details yet."}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-semibold tabular-nums">
                    <Money value={page.quote.price} decimals={2} />
                  </p>
                  <p className="text-xs text-slate-400">as of {page.quote.as_of}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    52W: <Money value={page.quote.low_52w} decimals={2} /> – <Money value={page.quote.high_52w} decimals={2} />
                  </p>
                </div>
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-900">Price History</h2>
                <div className="flex gap-1">
                  {RANGES.map((r) => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setRange(r)}
                      className={`rounded px-2 py-1 text-xs font-medium ${
                        range === r ? "bg-blue-50 text-blue-700" : "text-slate-500 hover:bg-slate-100"
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>
              <QueryState
                isLoading={pricesQuery.isLoading}
                isError={pricesQuery.isError}
                error={pricesQuery.error}
                data={pricesQuery.data}
                isEmpty={(d) => d.length === 0}
                emptyTitle="No price history for this range."
              >
                {(points) => <PriceChart points={points} />}
              </QueryState>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-slate-900">Fundamentals</h2>
              {page.latest_fundamentals ? (
                <FundamentalsGrid f={page.latest_fundamentals} />
              ) : (
                <p className="text-sm text-slate-400">No fundamentals data available yet.</p>
              )}
            </section>

            <ThesisSection ticker={page.ticker} thesis={page.thesis} />
          </>
        )}
      </QueryState>
    </div>
  );
}

type FundamentalsField = { label: string; value: string | null; kind: "text" | "money" | "percent" };

function FundamentalsGrid({ f }: { f: NonNullable<ReturnType<typeof useResearchPage>["data"]>["latest_fundamentals"] }) {
  if (!f) return null;
  const fields: FundamentalsField[] = [
    { label: "Period", value: f.period, kind: "text" },
    { label: "Revenue", value: f.revenue, kind: "money" },
    { label: "EPS", value: f.eps, kind: "money" },
    { label: "Gross Margin", value: f.gross_margin, kind: "percent" },
    { label: "Operating Margin", value: f.operating_margin, kind: "percent" },
    { label: "Net Margin", value: f.net_margin, kind: "percent" },
    { label: "ROE", value: f.roe, kind: "percent" },
    { label: "ROA", value: f.roa, kind: "percent" },
    { label: "Debt Ratio", value: f.debt_ratio, kind: "percent" },
    { label: "Operating Cash Flow", value: f.operating_cash_flow, kind: "money" },
    { label: "Free Cash Flow", value: f.free_cash_flow, kind: "money" },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {fields.map(({ label, value, kind }) => (
        <div key={label}>
          <p className="text-xs text-slate-400">{label}</p>
          <p className="text-sm font-medium tabular-nums text-slate-800">
            {kind === "text" && (value ?? "—")}
            {kind === "money" && <Money value={value} decimals={2} />}
            {kind === "percent" && <Percent value={value} colorBySign={false} />}
          </p>
        </div>
      ))}
      <p className="col-span-2 text-xs text-slate-400 md:col-span-4">Source: {f.source}</p>
    </div>
  );
}

function ThesisSection({ ticker, thesis }: { ticker: string; thesis: import("../types/api").Thesis | null }) {
  const [editing, setEditing] = useState(false);
  const upsertThesis = useUpsertThesis(ticker);

  const [text, setText] = useState(thesis?.thesis ?? "");
  const [catalysts, setCatalysts] = useState(thesis?.catalysts ?? "");
  const [risks, setRisks] = useState(thesis?.risks ?? "");
  const [status, setStatus] = useState<ThesisStatus>(thesis?.status ?? "INTACT");

  useEffect(() => {
    setText(thesis?.thesis ?? "");
    setCatalysts(thesis?.catalysts ?? "");
    setRisks(thesis?.risks ?? "");
    setStatus(thesis?.status ?? "INTACT");
  }, [thesis]);

  async function handleSave() {
    await upsertThesis.mutateAsync({ thesis: text, catalysts, risks, status });
    setEditing(false);
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Investment Thesis</h2>
        {thesis && !editing && <ThesisStatusBadge status={thesis.status} />}
      </div>

      {!editing ? (
        thesis ? (
          <div className="space-y-3 text-sm">
            <p className="text-slate-700">{thesis.thesis || <span className="text-slate-400">No thesis written yet.</span>}</p>
            {thesis.catalysts && (
              <div>
                <p className="text-xs font-medium text-slate-500">Catalysts</p>
                <p className="text-slate-700">{thesis.catalysts}</p>
              </div>
            )}
            {thesis.risks && (
              <div>
                <p className="text-xs font-medium text-slate-500">Risks</p>
                <p className="text-slate-700">{thesis.risks}</p>
              </div>
            )}
            {thesis.key_metrics && thesis.key_metrics.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium text-slate-500">Key Metrics</p>
                <div className="flex flex-wrap gap-2">
                  {thesis.key_metrics.map((m, i) => (
                    <span key={i} className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">
                      {m.label} {m.operator} {m.value}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <SecondaryButton type="button" onClick={() => setEditing(true)}>
              Edit
            </SecondaryButton>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-300 py-8 text-center">
            <p className="text-sm text-slate-500">No investment thesis yet for this stock.</p>
            <SecondaryButton type="button" className="mt-3" onClick={() => setEditing(true)}>
              Write a thesis
            </SecondaryButton>
          </div>
        )
      ) : (
        <div className="flex flex-col gap-3">
          <Field label="Why do I own / watch this stock?">
            <textarea className={`${inputClass} min-h-20`} value={text} onChange={(e) => setText(e.target.value)} />
          </Field>
          <Field label="Catalysts">
            <textarea className={`${inputClass} min-h-16`} value={catalysts} onChange={(e) => setCatalysts(e.target.value)} />
          </Field>
          <Field label="Risks">
            <textarea className={`${inputClass} min-h-16`} value={risks} onChange={(e) => setRisks(e.target.value)} />
          </Field>
          <Field label="Status">
            <select className={inputClass} value={status} onChange={(e) => setStatus(e.target.value as ThesisStatus)}>
              <option value="INTACT">INTACT</option>
              <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
              <option value="BROKEN">BROKEN</option>
            </select>
          </Field>
          {upsertThesis.isError && (
            <p className="text-sm text-red-600">
              {upsertThesis.error instanceof ApiRequestError ? upsertThesis.error.message : "Failed to save thesis."}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <SecondaryButton type="button" onClick={() => setEditing(false)}>
              Cancel
            </SecondaryButton>
            <PrimaryButton type="button" onClick={handleSave} disabled={upsertThesis.isPending}>
              {upsertThesis.isPending ? "Saving…" : "Save Thesis"}
            </PrimaryButton>
          </div>
        </div>
      )}
    </section>
  );
}
