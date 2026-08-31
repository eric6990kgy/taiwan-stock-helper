import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PricePoint } from "../types/api";
import { PriceChart } from "./PriceChart";

const candleSeries = { setData: vi.fn() };
const volumeSeries = { setData: vi.fn() };
const chart = {
  addSeries: vi.fn((definition: unknown) => (definition === "CandlestickSeries" ? candleSeries : volumeSeries)),
  priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
  timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
  applyOptions: vi.fn(),
  remove: vi.fn(),
};

// Rendering a real candlestick chart needs a canvas 2D context jsdom doesn't
// implement -- mock the library itself and assert on the data it was given,
// same approach the project already uses for provider HTTP calls (mocked
// transport, real normalization logic).
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => chart),
  CandlestickSeries: "CandlestickSeries",
  HistogramSeries: "HistogramSeries",
  ColorType: { Solid: "solid" },
}));

function point(overrides: Partial<PricePoint> = {}): PricePoint {
  return {
    date: "2026-08-28",
    open: "100.0000",
    high: "105.0000",
    low: "99.0000",
    close: "102.0000",
    volume: 1000,
    source: "FINMIND",
    ...overrides,
  };
}

describe("PriceChart", () => {
  it("renders nothing for an empty price series", () => {
    const { container } = render(<PriceChart points={[]} />);
    expect(container.querySelector('[data-testid="candlestick-chart"]')).not.toBeInTheDocument();
  });

  it("feeds candlestick and volume series from the price points", () => {
    render(<PriceChart points={[point()]} />);

    expect(candleSeries.setData).toHaveBeenCalledWith([
      { time: "2026-08-28", open: 100, high: 105, low: 99, close: 102 },
    ]);
    expect(volumeSeries.setData).toHaveBeenCalledWith([
      { time: "2026-08-28", value: 1000, color: "#16a34a" }, // close >= open -> up color
    ]);
  });

  it("colors a down day's volume bar with the down color", () => {
    render(<PriceChart points={[point({ open: "110.0000", close: "100.0000" })]} />);
    expect(volumeSeries.setData).toHaveBeenCalledWith([{ time: "2026-08-28", value: 1000, color: "#dc2626" }]);
  });

  it("skips a point missing OHLC (e.g. a MANUAL-source row) instead of fabricating candles", () => {
    render(<PriceChart points={[point({ open: null, high: null, low: null })]} />);
    expect(candleSeries.setData).toHaveBeenCalledWith([]);
  });
});
