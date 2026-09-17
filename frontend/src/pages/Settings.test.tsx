import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";
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

describe("Settings page — Accounts", () => {
  it("adds a new account and shows it in the list", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /add account/i }));
    await user.type(screen.getByLabelText(/^name$/i), "Test Brokerage");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: /^add account$/i })).not.toBeInTheDocument());
  });

  it("shows a validation error inline and keeps the modal open", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_URL}/api/accounts`, () => HttpResponse.json({ detail: "Name already in use." }, { status: 400 })),
    );
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /add account/i }));
    await user.type(screen.getByLabelText(/^name$/i), "Duplicate");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    expect(await screen.findByText("Name already in use.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^add account$/i })).toBeInTheDocument();
  });

  it("edits an existing account", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Settings />);

    await user.click((await screen.findAllByRole("button", { name: /^edit$/i }))[0]);
    expect(screen.getByText("Edit Account")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(screen.queryByText("Edit Account")).not.toBeInTheDocument());
  });

  it("surfaces a delete error inline instead of failing silently (e.g. blocked by existing transactions)", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    server.use(
      http.delete(`${API_URL}/api/accounts/:id`, () =>
        HttpResponse.json(
          { detail: "Cannot delete account 1: it still has transactions. Delete its transactions first, or reassign them to another account." },
          { status: 400 },
        ),
      ),
    );
    renderWithProviders(<Settings />);

    await user.click((await screen.findAllByRole("button", { name: /^delete$/i }))[0]);

    expect(await screen.findByText(/still has transactions/i)).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it("asks for confirmation before deleting an account, and does nothing if declined", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    let deleteCalled = false;
    server.use(
      http.delete(`${API_URL}/api/accounts/:id`, () => {
        deleteCalled = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderWithProviders(<Settings />);

    await user.click((await screen.findAllByRole("button", { name: /^delete$/i }))[0]);

    expect(confirmSpy).toHaveBeenCalled();
    expect(deleteCalled).toBe(false);
    confirmSpy.mockRestore();
  });
});

describe("Settings page — Assets", () => {
  it("adds a new asset", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /add asset/i }));
    await user.type(screen.getByLabelText(/^ticker$/i), "2330");
    await user.type(screen.getByLabelText(/^name$/i), "台積電");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: /^add asset$/i })).not.toBeInTheDocument());
  });

  it("shows a friendly message for a duplicate ticker (409)", async () => {
    const user = userEvent.setup();
    server.use(http.post(`${API_URL}/api/assets`, () => HttpResponse.json({ detail: "ticker exists" }, { status: 409 })));
    renderWithProviders(<Settings />);

    await user.click(await screen.findByRole("button", { name: /add asset/i }));
    await user.type(screen.getByLabelText(/^ticker$/i), "3653");
    await user.type(screen.getByLabelText(/^name$/i), "健策");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    expect(await screen.findByText(/已存在/)).toBeInTheDocument();
  });
});

describe("Settings page — Data Import / Export", () => {
  it("renders the three export download links", async () => {
    renderWithProviders(<Settings />);
    expect(await screen.findByRole("link", { name: /transactions\.csv/i })).toHaveAttribute(
      "href",
      `${API_URL}/api/export/transactions`,
    );
    expect(screen.getByRole("link", { name: /holdings\.csv/i })).toHaveAttribute("href", `${API_URL}/api/export/holdings`);
    expect(screen.getByRole("link", { name: /portfolio-snapshot\.csv/i })).toHaveAttribute(
      "href",
      `${API_URL}/api/export/portfolio-snapshot`,
    );
  });

  it("imports a CSV and shows the imported count", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Settings />);

    const file = new File(["account_name,ticker,date,type,quantity,price,fee,tax,currency,note\n"], "t.csv", {
      type: "text/csv",
    });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: /^import$/i }));

    expect(await screen.findByText(/imported 1 row/i)).toBeInTheDocument();
  });

  it("shows skipped rows and needs-review tickers", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_URL}/api/import/transactions`, () =>
        HttpResponse.json({
          imported: 1,
          skipped: [{ row: 3, reason: "Unknown account: Foo" }],
          needs_review_tickers: ["9999"],
        }),
      ),
    );
    renderWithProviders(<Settings />);

    const file = new File(["account_name,ticker,date,type,quantity,price,fee,tax,currency,note\n"], "t.csv", {
      type: "text/csv",
    });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: /^import$/i }));

    expect(await screen.findByText(/unknown account: foo/i)).toBeInTheDocument();
    expect(screen.getByText("9999")).toBeInTheDocument();
  });

  it("shows the backend's message when a required column is missing", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_URL}/api/import/transactions`, () =>
        HttpResponse.json({ detail: "Missing required column: ticker" }, { status: 400 }),
      ),
    );
    renderWithProviders(<Settings />);

    const file = new File(["bad,header\n"], "t.csv", { type: "text/csv" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: /^import$/i }));

    expect(await screen.findByText(/missing required column/i)).toBeInTheDocument();
  });
});
