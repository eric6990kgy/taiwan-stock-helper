import { formatCurrency, formatPercent, formatShares, SIGN_TEXT_CLASS, signOf } from "../utils/decimal";

interface MoneyProps {
  value: string | null | undefined;
  currency?: string;
  decimals?: number;
  colorBySign?: boolean;
  className?: string;
}

export function Money({ value, currency = "TWD", decimals = 0, colorBySign = false, className = "" }: MoneyProps) {
  const colorClass = colorBySign ? SIGN_TEXT_CLASS[signOf(value)] : "";
  return <span className={`tabular-nums ${colorClass} ${className}`}>{formatCurrency(value, currency, decimals)}</span>;
}

interface PercentProps {
  value: string | null | undefined;
  decimals?: number;
  colorBySign?: boolean;
  className?: string;
}

export function Percent({ value, decimals = 2, colorBySign = true, className = "" }: PercentProps) {
  const colorClass = colorBySign ? SIGN_TEXT_CLASS[signOf(value)] : "";
  return <span className={`tabular-nums ${colorClass} ${className}`}>{formatPercent(value, decimals)}</span>;
}

export function Shares({ value, className = "" }: { value: string | null | undefined; className?: string }) {
  return <span className={`tabular-nums ${className}`}>{formatShares(value)}</span>;
}
