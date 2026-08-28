import { describe, expect, it } from "vitest";
import { formatCurrency, formatMoney, formatPercent, formatShares, signOf } from "./decimal";

describe("formatMoney", () => {
  it("groups thousands without touching precision", () => {
    expect(formatMoney("135750.00000000")).toBe("135,750");
  });

  it("keeps requested decimal places", () => {
    expect(formatMoney("628.8000", 2)).toBe("628.80");
  });

  it("handles negative values", () => {
    expect(formatMoney("-49514.00000000")).toBe("-49,514");
  });

  it("returns an em dash for null/undefined", () => {
    expect(formatMoney(null)).toBe("—");
    expect(formatMoney(undefined)).toBe("—");
  });

  it("never round-trips through a JS float (precision-sensitive value)", () => {
    // 0.1 + 0.2 !== 0.3 in float -- this exercises a value that would
    // reveal float contamination if formatMoney used Number() anywhere.
    expect(formatMoney("100000000000000.1234", 4)).toBe("100,000,000,000,000.1234");
  });
});

describe("formatCurrency", () => {
  it("prefixes TWD with NT$", () => {
    expect(formatCurrency("1000")).toBe("NT$1,000");
  });

  it("prefixes other currencies with the code", () => {
    expect(formatCurrency("1000", "USD")).toBe("USD 1,000");
  });
});

describe("formatPercent", () => {
  it("converts a fraction to a signed percentage", () => {
    expect(formatPercent("0.0823")).toBe("+8.23%");
  });

  it("signs negative values", () => {
    expect(formatPercent("-0.0314")).toBe("-3.14%");
  });

  it("returns an em dash for null (no fake 0%)", () => {
    expect(formatPercent(null)).toBe("—");
  });
});

describe("formatShares", () => {
  it("trims fixed-scale trailing zeros", () => {
    expect(formatShares("15.0000")).toBe("15");
    expect(formatShares("302.5000")).toBe("302.5");
    expect(formatShares("120000.0000")).toBe("120000");
  });

  it("returns an em dash for null/undefined", () => {
    expect(formatShares(null)).toBe("—");
  });
});

describe("signOf", () => {
  it("classifies positive, negative, and zero", () => {
    expect(signOf("100")).toBe("positive");
    expect(signOf("-100")).toBe("negative");
    expect(signOf("0")).toBe("neutral");
  });

  it("treats null as neutral", () => {
    expect(signOf(null)).toBe("neutral");
  });
});
