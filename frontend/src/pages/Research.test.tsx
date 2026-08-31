import { screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
import { Research } from "./Research";

const API_URL = "http://127.0.0.1:8010";

// Same rationale as PriceChart.test.tsx -- avoid exercising real canvas
// rendering in jsdom.
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({ setData: vi.fn() })),
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  })),
  CandlestickSeries: "CandlestickSeries",
  HistogramSeries: "HistogramSeries",
  ColorType: { Solid: "solid" },
}));

const mockAssetsForResearch = [
  { id: 1, ticker: "3653", name: "健策", asset_type: "STOCK", market: "TWSE", currency: "TWD", sector: "Tech", industry: "Semis", valuation_method: "TRANSACTION_BASED", is_demo_data: true, needs_review: false },
];

const mockResearchPage = {
  ticker: "3653",
  name: "健策",
  asset_type: "STOCK",
  market: "TWSE",
  sector: "Technology",
  industry: "Semiconductor Packaging",
  is_demo_data: true,
  quote: { ticker: "3653", price: "650.0000", as_of: "2026-08-28", high_52w: "700.0000", low_52w: "600.0000" },
  latest_fundamentals: null,
  thesis: null,
};

const mockPrices = [
  { date: "2026-08-27", open: "640.0000", high: "655.0000", low: "635.0000", close: "648.0000", volume: 1000000, source: "MOCK" },
  { date: "2026-08-28", open: "648.0000", high: "660.0000", low: "645.0000", close: "650.0000", volume: 1200000, source: "MOCK" },
];

const mockTechnical = {
  ticker: "3653",
  as_of: "2026-08-28",
  indicators: {
    sma_5: "645.0000",
    sma_20: null,
    ema_20: null,
    rsi_14: null,
    macd: null,
    macd_signal: null,
    macd_histogram: null,
    bollinger_upper: null,
    bollinger_middle: null,
    bollinger_lower: null,
    kd_k: null,
    kd_d: null,
  },
  source: "CALCULATED",
};

const mockInstitutionalFlows = [
  {
    date: "2026-08-28",
    foreign_buy: 1000000,
    foreign_sell: 400000,
    foreign_net: 600000,
    investment_trust_buy: 20000,
    investment_trust_sell: 5000,
    investment_trust_net: 15000,
    dealer_buy: 1000,
    dealer_sell: 500,
    dealer_net: 500,
    total_net: 615500,
    source: "FINMIND",
  },
];

const mockMargin = [
  {
    date: "2026-08-28",
    margin_buy: 100,
    margin_sell: 50,
    margin_cash_repayment: 5,
    margin_balance: 28308,
    short_sale_buy: 1,
    short_sale_sell: 2,
    short_sale_cash_repayment: 0,
    short_sale_balance: 30,
    source: "FINMIND",
  },
];

const mockRevenue = [
  { revenue_year: 2026, revenue_month: 7, revenue: "467580548000.0000", yoy_growth: "0.05", mom_growth: null, announcement_date: "2026-08-01", source: "FINMIND" },
];

function setupHandlers() {
  server.use(
    http.get(`${API_URL}/api/assets`, () => HttpResponse.json(mockAssetsForResearch)),
    http.get(`${API_URL}/api/research/3653`, () => HttpResponse.json(mockResearchPage)),
    http.get(`${API_URL}/api/prices/3653`, () => HttpResponse.json(mockPrices)),
    http.get(`${API_URL}/api/research/3653/technical`, () => HttpResponse.json(mockTechnical)),
    http.get(`${API_URL}/api/research/3653/institutional`, () => HttpResponse.json(mockInstitutionalFlows)),
    http.get(`${API_URL}/api/research/3653/margin`, () => HttpResponse.json(mockMargin)),
    http.get(`${API_URL}/api/research/3653/revenue`, () => HttpResponse.json(mockRevenue)),
  );
}

describe("Research page -- Phase 6 sections", () => {
  it("shows a loading state before data arrives", async () => {
    setupHandlers();
    renderWithProviders(<Research />);
    expect(screen.getAllByText(/loading/i).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.getByText("健策")).toBeInTheDocument());
  });

  it("renders the candlestick chart container once prices load", async () => {
    setupHandlers();
    renderWithProviders(<Research />);
    expect(await screen.findByTestId("candlestick-chart")).toBeInTheDocument();
  });

  it("renders technical indicators and marks a missing indicator honestly, not as zero", async () => {
    setupHandlers();
    renderWithProviders(<Research />);
    expect(await screen.findByText("645.00")).toBeInTheDocument(); // SMA 5
    // sma_20 is null in the mock -- rendered as an em dash, never "0.00".
    const smaTwentyLabel = await screen.findByText("SMA 20");
    expect(smaTwentyLabel.nextElementSibling?.textContent).toBe("—");
  });

  it("renders the institutional flow section with the three-way split", async () => {
    setupHandlers();
    renderWithProviders(<Research />);
    expect(await screen.findByText("Institutional Flow (三大法人)")).toBeInTheDocument();
    expect(await screen.findByText("外資 Foreign")).toBeInTheDocument();
    expect(await screen.findByText("600,000")).toBeInTheDocument(); // foreign_net
  });

  it("renders the margin trading section in 張 (lots)", async () => {
    setupHandlers();
    renderWithProviders(<Research />);
    expect(await screen.findByText("Margin Trading (融資融券)")).toBeInTheDocument();
    // 28,308 appears in both the summary card and the recent-days table row.
    expect((await screen.findAllByText("28,308")).length).toBeGreaterThanOrEqual(1);
  });

  it("renders the monthly revenue section with computed growth", async () => {
    setupHandlers();
    renderWithProviders(<Research />);
    expect(await screen.findByText("Monthly Revenue (月營收)")).toBeInTheDocument();
    expect(await screen.findByText("2026-07")).toBeInTheDocument();
    expect(await screen.findByText("+5.00%")).toBeInTheDocument(); // yoy_growth
  });

  it("shows an honest empty state for institutional flow when nothing has been ingested", async () => {
    server.use(
      http.get(`${API_URL}/api/assets`, () => HttpResponse.json(mockAssetsForResearch)),
      http.get(`${API_URL}/api/research/3653`, () => HttpResponse.json(mockResearchPage)),
      http.get(`${API_URL}/api/prices/3653`, () => HttpResponse.json(mockPrices)),
      http.get(`${API_URL}/api/research/3653/technical`, () => HttpResponse.json(mockTechnical)),
      http.get(`${API_URL}/api/research/3653/institutional`, () => HttpResponse.json([])),
      http.get(`${API_URL}/api/research/3653/margin`, () => HttpResponse.json([])),
      http.get(`${API_URL}/api/research/3653/revenue`, () => HttpResponse.json([])),
    );
    renderWithProviders(<Research />);
    expect(await screen.findByText(/no institutional flow data ingested yet/i)).toBeInTheDocument();
    expect(await screen.findByText(/no margin trading data ingested yet/i)).toBeInTheDocument();
    expect(await screen.findByText(/no monthly revenue data ingested yet/i)).toBeInTheDocument();
  });

  it("shows an error state when the technical indicators request fails", async () => {
    server.use(
      http.get(`${API_URL}/api/assets`, () => HttpResponse.json(mockAssetsForResearch)),
      http.get(`${API_URL}/api/research/3653`, () => HttpResponse.json(mockResearchPage)),
      http.get(`${API_URL}/api/prices/3653`, () => HttpResponse.json(mockPrices)),
      http.get(`${API_URL}/api/research/3653/technical`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
      http.get(`${API_URL}/api/research/3653/institutional`, () => HttpResponse.json([])),
      http.get(`${API_URL}/api/research/3653/margin`, () => HttpResponse.json([])),
      http.get(`${API_URL}/api/research/3653/revenue`, () => HttpResponse.json([])),
    );
    renderWithProviders(<Research />);
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });
});
