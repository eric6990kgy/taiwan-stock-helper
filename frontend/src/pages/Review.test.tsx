import { fireEvent, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
import { Review } from "./Review";

const API_URL = "http://127.0.0.1:8010";

function outcome(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    recommendation_id: 1,
    ticker: "2330",
    asset_name: "台積電",
    action: "CONSIDER_INCREASE",
    call: "BULLISH",
    actual_direction: "BULLISH",
    hit: true,
    horizon_trading_days: 5,
    as_of_date: "2026-09-01",
    outcome_date: "2026-09-08",
    from_close: "600.0000",
    to_close: "630.0000",
    risk_blocked: false,
    computed_at: "2026-09-09T08:00:00Z",
    ...overrides,
  };
}

describe("Review page", () => {
  it("shows 'insufficient sample' instead of a fabricated rate when nothing is scored", async () => {
    renderWithProviders(<Review />);
    expect(await screen.findAllByText(/insufficient sample/i)).not.toHaveLength(0);
  });

  it("shows an honest empty state for the outcomes list before anything is scored", async () => {
    renderWithProviders(<Review />);
    expect(await screen.findByText(/nothing scored yet/i)).toBeInTheDocument();
  });

  it("renders the overall hit rate once outcomes exist", async () => {
    server.use(
      http.get(`${API_URL}/api/review/summary`, ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get("action")) return HttpResponse.json({ hits: 0, n: 0, hit_rate: null });
        return HttpResponse.json({ hits: 3, n: 4, hit_rate: "0.75" });
      }),
      http.get(`${API_URL}/api/review/outcomes`, () => HttpResponse.json([outcome()])),
    );
    renderWithProviders(<Review />);
    expect(await screen.findByText(/75\.0% \(3\/4\)/)).toBeInTheDocument();
  });

  it("shows a Hit or Miss badge per scored recommendation", async () => {
    server.use(http.get(`${API_URL}/api/review/outcomes`, () => HttpResponse.json([outcome(), outcome({ id: 2, ticker: "2454", hit: false })])));
    renderWithProviders(<Review />);
    expect(await screen.findByText("Hit")).toBeInTheDocument();
    expect(await screen.findByText("Miss")).toBeInTheDocument();
  });

  it("expands a row to show the call vs. actual direction and prices", async () => {
    server.use(http.get(`${API_URL}/api/review/outcomes`, () => HttpResponse.json([outcome()])));
    renderWithProviders(<Review />);
    const row = await screen.findByText("2330");
    expect(screen.queryByText(/630\.0000/)).not.toBeInTheDocument();
    fireEvent.click(row);
    expect(await screen.findByText(/630\.0000/)).toBeInTheDocument();
  });

  it("shows an error state when the outcomes request fails", async () => {
    server.use(http.get(`${API_URL}/api/review/outcomes`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));
    renderWithProviders(<Review />);
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });
});
