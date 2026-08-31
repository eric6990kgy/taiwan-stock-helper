import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
import { Settings } from "./Settings";

const API_URL = "http://127.0.0.1:8010";

describe("Settings page — Update Market Data", () => {
  it("shows a completed result with succeeded tickers, source, and as-of date", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /update market data/i }));

    expect(await screen.findByText("Completed")).toBeInTheDocument();
    expect(screen.getByText(/7 assets processed/i)).toBeInTheDocument();
    expect(screen.getByText("FINMIND")).toBeInTheDocument();
    expect(screen.getByText(/2026-08-28/)).toBeInTheDocument();
    expect(screen.getByText(/3653, 3533, 3491/)).toBeInTheDocument();
    expect(screen.getByText("Failed (0)")).toBeInTheDocument();
  });

  it("disables the button and shows a pending label while the update is in flight", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_URL}/api/market-data/update`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return HttpResponse.json({
          status: "completed",
          assets_processed: 1,
          succeeded: ["3653"],
          failed: [],
          validation_warnings: [],
          latest_data_date: "2026-08-28",
          source: "FINMIND",
        });
      }),
    );
    renderWithProviders(<Settings />);

    const button = await screen.findByRole("button", { name: /update market data/i });
    await user.click(button);

    expect(await screen.findByRole("button", { name: /updating/i })).toBeDisabled();
    await waitFor(() => expect(screen.getByText("Completed")).toBeInTheDocument());
  });

  it("shows failed tickers and reasons when the batch reports partial failure", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_URL}/api/market-data/update`, () =>
        HttpResponse.json({
          status: "completed",
          assets_processed: 2,
          succeeded: ["3653"],
          failed: [{ ticker: "3533", reason: "FinMind is unreachable" }],
          validation_warnings: [],
          latest_data_date: "2026-08-28",
          source: "FINMIND",
        }),
      ),
    );
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /update market data/i }));

    expect(await screen.findByText("Failed (1)")).toBeInTheDocument();
    expect(screen.getByText(/FinMind is unreachable/)).toBeInTheDocument();
  });

  it("shows a rate-limited status distinctly from a completed one", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_URL}/api/market-data/update`, () =>
        HttpResponse.json({
          status: "rate_limited",
          assets_processed: 3,
          succeeded: ["3653"],
          failed: [
            { ticker: "3533", reason: "Rate limited: quota exceeded" },
            { ticker: "3491", reason: "Skipped: update stopped after rate limit." },
          ],
          validation_warnings: [],
          latest_data_date: "2026-08-28",
          source: "FINMIND",
        }),
      ),
    );
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /update market data/i }));

    expect(await screen.findByText(/stopped — rate limited/i)).toBeInTheDocument();
    expect(screen.getByText(/quota exceeded/)).toBeInTheDocument();
    expect(screen.getByText(/skipped: update stopped/i)).toBeInTheDocument();
  });

  it("shows validation warnings separately from failures", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_URL}/api/market-data/update`, () =>
        HttpResponse.json({
          status: "completed",
          assets_processed: 1,
          succeeded: ["3653"],
          failed: [],
          validation_warnings: [{ ticker: "3653", reason: "2026-08-28: close must be > 0 (got Decimal('0'))." }],
          latest_data_date: "2026-08-27",
          source: "FINMIND",
        }),
      ),
    );
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /update market data/i }));

    expect(await screen.findByText(/validation warnings \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/close must be > 0/)).toBeInTheDocument();
  });

  it("shows an error message when the update request itself fails", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_URL}/api/market-data/update`, () => HttpResponse.json({ detail: "backend down" }, { status: 500 })),
    );
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /update market data/i }));

    expect(await screen.findByText("backend down")).toBeInTheDocument();
  });
});
