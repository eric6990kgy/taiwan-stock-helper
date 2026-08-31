import type { TechnicalIndicators } from "../types/api";
import { formatMoney } from "../utils/decimal";

interface TechnicalIndicatorsPanelProps {
  data: TechnicalIndicators;
}

type Field = { label: string; value: string | null };

/** All values are pre-computed by the backend (app.analytics.technical) --
 * this component only formats and labels them, per Sec.18: a calculated
 * indicator must never be presented as if it came straight from the data
 * provider, hence the explicit "Source: CALCULATED" footer. */
export function TechnicalIndicatorsPanel({ data }: TechnicalIndicatorsPanelProps) {
  if (data.as_of === null) {
    return <p className="text-sm text-slate-400">Not enough price history to calculate technical indicators yet.</p>;
  }

  const { indicators } = data;
  const fields: Field[] = [
    { label: "SMA 5", value: indicators.sma_5 },
    { label: "SMA 20", value: indicators.sma_20 },
    { label: "EMA 20", value: indicators.ema_20 },
    { label: "RSI 14", value: indicators.rsi_14 },
    { label: "MACD", value: indicators.macd },
    { label: "MACD Signal", value: indicators.macd_signal },
    { label: "MACD Histogram", value: indicators.macd_histogram },
    { label: "Bollinger Upper", value: indicators.bollinger_upper },
    { label: "Bollinger Middle", value: indicators.bollinger_middle },
    { label: "Bollinger Lower", value: indicators.bollinger_lower },
    { label: "KD %K", value: indicators.kd_k },
    { label: "KD %D", value: indicators.kd_d },
  ];

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {fields.map(({ label, value }) => (
          <div key={label}>
            <p className="text-xs text-slate-400">{label}</p>
            <p className="text-sm font-medium tabular-nums text-slate-800">{formatMoney(value, 2)}</p>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-400">
        As of {data.as_of}. Source: {data.source} — computed from price history, not a provider field.
      </p>
    </div>
  );
}
