import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  createChart,
  type CandlestickData,
  type HistogramData,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { PricePoint } from "../types/api";

interface PriceChartProps {
  points: PricePoint[];
}

const UP_COLOR = "#16a34a"; // matches --color-positive (utils/decimal.ts)
const DOWN_COLOR = "#dc2626"; // matches --color-negative

/** Candlestick + volume chart (Phase 6, replacing the Phase 4 line chart --
 * Integration Report Sec.7: a line chart loses OHLC pattern information a
 * candlestick chart keeps). lightweight-charts is used purely for chart
 * geometry -- every number here is a raw API field converted to a JS
 * number only for pixel placement, never for any P&L/cost-basis math (that
 * stays in app.analytics on the backend, same rule the old chart followed).
 */
export function PriceChart({ points }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 320,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#475569", fontSize: 11 },
      grid: { vertLines: { color: "#e2e8f0" }, horzLines: { color: "#e2e8f0" } },
      rightPriceScale: { borderColor: "#e2e8f0" },
      timeScale: { borderColor: "#e2e8f0" },
      crosshair: { mode: 0 },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: UP_COLOR,
      downColor: DOWN_COLOR,
      borderVisible: false,
      wickUpColor: UP_COLOR,
      wickDownColor: DOWN_COLOR,
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    const candleData: CandlestickData[] = [];
    const volumeData: HistogramData[] = [];
    for (const p of points) {
      const time = p.date as unknown as UTCTimestamp; // 'YYYY-MM-DD' is accepted directly as a business day string
      const close = Number(p.close);
      // A row missing open/high/low (e.g. a MANUAL-source point, which only
      // ever carries a close) can't be drawn as a real candle -- rather than
      // dropping the point (the old line chart plotted every point using
      // close alone), draw a flat candle at close. That's honest: it shows
      // the one value actually known, without fabricating an intraday range.
      const open = p.open !== null ? Number(p.open) : close;
      const high = p.high !== null ? Number(p.high) : close;
      const low = p.low !== null ? Number(p.low) : close;
      candleData.push({ time, open, high, low, close });
      if (p.volume !== null) {
        volumeData.push({ time, value: p.volume, color: close >= open ? UP_COLOR : DOWN_COLOR });
      }
    }
    candleSeries.setData(candleData);
    volumeSeries.setData(volumeData);
    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [points]);

  if (points.length === 0) return null;

  return <div ref={containerRef} className="w-full" data-testid="candlestick-chart" />;
}
