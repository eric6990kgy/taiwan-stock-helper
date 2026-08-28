/**
 * All formatting here goes through decimal.js, never `Number()`/`parseFloat`,
 * so a value the backend sent as an exact string is never quietly rounded
 * through IEEE-754 before it's just being *displayed*. Nothing in this file
 * combines two Decimals arithmetically -- that's the backend's job
 * (app.analytics); this only rounds and punctuates a single already-computed
 * value for presentation (PRD Sec.36, Principle 3).
 */
import Decimal from "decimal.js";

export function toDecimal(value: string | number): Decimal {
  return new Decimal(value);
}

/** "1234567.891" -> "1,234,568" (TWD has no minor unit in everyday display). */
export function formatMoney(value: string | null | undefined, decimals = 0): string {
  if (value === null || value === undefined) return "—";
  const d = new Decimal(value).toDecimalPlaces(decimals, Decimal.ROUND_HALF_UP);
  const [intPart, fracPart] = d.toFixed(decimals).split(".");
  const negative = intPart.startsWith("-");
  const digits = negative ? intPart.slice(1) : intPart;
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const sign = negative ? "-" : "";
  return fracPart ? `${sign}${grouped}.${fracPart}` : `${sign}${grouped}`;
}

export function formatCurrency(value: string | null | undefined, currency = "TWD", decimals = 0): string {
  if (value === null || value === undefined) return "—";
  const symbol = currency === "TWD" ? "NT$" : `${currency} `;
  return `${symbol}${formatMoney(value, decimals)}`;
}

/** A fraction like "0.0823" -> "+8.23%"; null -> "—" (no fake 0%, matches
 * the backend's None-means-"not meaningful" convention). */
export function formatPercent(value: string | null | undefined, decimals = 2): string {
  if (value === null || value === undefined) return "—";
  const pct = new Decimal(value).times(100).toDecimalPlaces(decimals, Decimal.ROUND_HALF_UP);
  const sign = pct.gte(0) ? "+" : "";
  return `${sign}${pct.toFixed(decimals)}%`;
}

/** Share counts: trims the fixed-scale trailing zeros the API sends
 * ("15.0000" -> "15", "302.5000" -> "302.5") without touching precision. */
export function formatShares(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  let s = new Decimal(value).toFixed(); // fixed (non-exponential) notation
  if (s.includes(".")) {
    s = s.replace(/0+$/, "").replace(/\.$/, "");
  }
  return s;
}

export type Sign = "positive" | "negative" | "neutral";

export function signOf(value: string | null | undefined): Sign {
  if (value === null || value === undefined) return "neutral";
  const d = new Decimal(value);
  if (d.gt(0)) return "positive";
  if (d.lt(0)) return "negative";
  return "neutral";
}

export const SIGN_TEXT_CLASS: Record<Sign, string> = {
  positive: "text-[color:var(--color-positive)]",
  negative: "text-[color:var(--color-negative)]",
  neutral: "text-[color:var(--color-neutral)]",
};
