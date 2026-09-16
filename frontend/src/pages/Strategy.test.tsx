import { fireEvent, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
import { Strategy } from "./Strategy";

const API_URL = "http://127.0.0.1:8010";

const activeVersion = {
  id: 1,
  version_number: 1,
  rules: { sma_short: 20, sma_long: 60, rsi_period: 14, institutional_window: 5, composite_bullish: "60", composite_bearish: "40" },
  status: "ACTIVE",
  change_type: "AUTO_APPLIED",
  reason: "Initial default strategy",
  backtest_hit_rate: "0.6500",
  backtest_n: 40,
  created_at: "2026-09-01T00:00:00Z",
};

function setupHandlers(pending: unknown[] = []) {
  server.use(
    http.get(`${API_URL}/api/strategy/versions`, () => HttpResponse.json([activeVersion])),
    http.get(`${API_URL}/api/strategy/pending`, () => HttpResponse.json(pending)),
  );
}

describe("Strategy page", () => {
  it("shows the active version's rules", async () => {
    setupHandlers();
    renderWithProviders(<Strategy />);
    // "v1" and the reason text each appear in both the Active Version card
    // and the History table row.
    expect((await screen.findAllByText("v1")).length).toBe(2);
    expect((await screen.findAllByText("Initial default strategy")).length).toBe(2);
    expect(await screen.findByText("sma_short")).toBeInTheDocument();
  });

  it("shows an honest empty state when nothing is pending", async () => {
    setupHandlers([]);
    renderWithProviders(<Strategy />);
    expect(await screen.findByText(/no changes awaiting confirmation/i)).toBeInTheDocument();
  });

  it("renders a pending change with backtest before/after and confirm/reject actions", async () => {
    setupHandlers([
      {
        id: 5,
        proposed_rules: { ...activeVersion.rules, sma_short: 25 },
        reason: "Widen the short SMA window",
        backtest_before: { hits: 20, n: 40, horizon: 5, deadzone_pct: "1", hit_rate: "0.5000" },
        backtest_after: { hits: 26, n: 40, horizon: 5, deadzone_pct: "1", hit_rate: "0.6500" },
        status: "PENDING",
        created_at: "2026-09-16T00:00:00Z",
        decided_at: null,
      },
    ]);
    renderWithProviders(<Strategy />);
    expect(await screen.findByText("Widen the short SMA window")).toBeInTheDocument();
    expect(await screen.findByText(/before:\s*50\.0%/i)).toBeInTheDocument();
    expect(await screen.findByText(/after:\s*65\.0%/i)).toBeInTheDocument();
    expect(await screen.findByText("Confirm")).toBeInTheDocument();
    expect(await screen.findByText("Reject")).toBeInTheDocument();
  });

  it("confirms a pending change", async () => {
    setupHandlers([
      {
        id: 5,
        proposed_rules: { ...activeVersion.rules, sma_short: 25 },
        reason: "Widen the short SMA window",
        backtest_before: null,
        backtest_after: null,
        status: "PENDING",
        created_at: "2026-09-16T00:00:00Z",
        decided_at: null,
      },
    ]);
    let confirmed = false;
    server.use(
      http.post(`${API_URL}/api/strategy/pending/5/confirm`, () => {
        confirmed = true;
        return HttpResponse.json({ ...activeVersion, id: 2, version_number: 2, change_type: "CONFIRMED" });
      }),
    );
    renderWithProviders(<Strategy />);
    fireEvent.click(await screen.findByText("Confirm"));
    await waitFor(() => expect(confirmed).toBe(true));
  });

  it("shows an error state when versions fail to load", async () => {
    server.use(
      http.get(`${API_URL}/api/strategy/versions`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
      http.get(`${API_URL}/api/strategy/pending`, () => HttpResponse.json([])),
    );
    renderWithProviders(<Strategy />);
    // Both the "Active Version" and "Version History" sections share the
    // same failing query, so the error renders in both places.
    expect((await screen.findAllByText("boom")).length).toBeGreaterThan(0);
  });
});
