import { fireEvent, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
import { Recommendations } from "./Recommendations";

const API_URL = "http://127.0.0.1:8010";

function recommendation(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    ticker: "2330",
    asset_name: "台積電",
    action: "CONSIDER_INCREASE",
    previous_status: "NEUTRAL",
    new_status: "BULLISH",
    triggered_signals: [
      { id: "PRICE_ABOVE_SMA20", category: "TECHNICAL", name: "股價站上20日均線", status: "BULLISH", explanation: "股價站上20日均線" },
    ],
    risk_blocked: false,
    risk_block_reason: null,
    composite_score: "68.20",
    regime: "BULL",
    strategy_version_id: 1,
    created_at: "2026-09-16T08:00:00Z",
    ...overrides,
  };
}

describe("Recommendations page", () => {
  it("shows an honest empty state before any scan has run", async () => {
    server.use(http.get(`${API_URL}/api/recommendations`, () => HttpResponse.json([])));
    renderWithProviders(<Recommendations />);
    expect(await screen.findByText(/no recommendations yet/i)).toBeInTheDocument();
  });

  it("renders a recommendation row with its action and status transition", async () => {
    server.use(http.get(`${API_URL}/api/recommendations`, () => HttpResponse.json([recommendation()])));
    renderWithProviders(<Recommendations />);
    expect(await screen.findByText("2330")).toBeInTheDocument();
    expect(await screen.findByText("Consider Increasing")).toBeInTheDocument();
  });

  it("visually distinguishes a risk-blocked recommendation from an ordinary one", async () => {
    server.use(
      http.get(`${API_URL}/api/recommendations`, () =>
        HttpResponse.json([recommendation({ id: 2, risk_blocked: true, risk_block_reason: "目前回撤處於 HARD_STOP" })]),
      ),
    );
    renderWithProviders(<Recommendations />);
    expect(await screen.findByText(/risk blocked/i)).toBeInTheDocument();
  });

  it("expands a row to show the risk-block reason and triggered signals", async () => {
    server.use(
      http.get(`${API_URL}/api/recommendations`, () =>
        HttpResponse.json([recommendation({ risk_blocked: true, risk_block_reason: "目前回撤處於 HARD_STOP" })]),
      ),
    );
    renderWithProviders(<Recommendations />);
    const row = await screen.findByText("2330");
    expect(screen.queryByText("目前回撤處於 HARD_STOP")).not.toBeInTheDocument();
    fireEvent.click(row);
    expect(await screen.findByText("目前回撤處於 HARD_STOP")).toBeInTheDocument();
    expect(await screen.findByText("股價站上20日均線")).toBeInTheDocument();
  });

  it("shows an error state when the request fails", async () => {
    server.use(http.get(`${API_URL}/api/recommendations`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));
    renderWithProviders(<Recommendations />);
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });
});
