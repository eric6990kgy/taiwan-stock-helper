import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
import type { Asset } from "../types/api";
import { Transactions } from "./Transactions";

const API_URL = "http://127.0.0.1:8010";

describe("Transactions page", () => {
  it("shows the empty state when there are no transactions", async () => {
    renderWithProviders(<Transactions />);
    expect(await screen.findByText(/no transactions yet/i)).toBeInTheDocument();
  });

  it("opens the Add Transaction modal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Transactions />);
    await user.click(await screen.findByRole("button", { name: /add transaction/i }));
    expect(screen.getByRole("heading", { name: /add transaction/i })).toBeInTheDocument();
  });

  it("surfaces the backend's insufficient-shares error message in the form instead of failing silently", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Transactions />);

    await user.click(await screen.findByRole("button", { name: /add transaction/i }));

    const accountSelect = await screen.findByRole("combobox", { name: /account/i });
    await user.selectOptions(accountSelect, "1");
    const assetSelect = screen.getByRole("combobox", { name: /asset/i });
    await user.selectOptions(assetSelect, "1");

    const quantityInputs = screen.getAllByRole("spinbutton");
    await user.type(quantityInputs[0], "999");
    await user.type(quantityInputs[1], "100");

    await user.click(screen.getByRole("button", { name: /save transaction/i }));

    await waitFor(() => expect(screen.getByText(/only 3\.0000 available/i)).toBeInTheDocument());
    // The modal must stay open on failure -- the user's input isn't lost.
    expect(screen.getByRole("heading", { name: /add transaction/i })).toBeInTheDocument();
  });

  it("rejects a zero quantity client-side instead of hitting a confusing 422", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Transactions />);

    await user.click(await screen.findByRole("button", { name: /add transaction/i }));
    const accountSelect = await screen.findByRole("combobox", { name: /account/i });
    await user.selectOptions(accountSelect, "1");
    const assetSelect = screen.getByRole("combobox", { name: /asset/i });
    await user.selectOptions(assetSelect, "1");

    const [quantityInput, priceInput] = screen.getAllByRole("spinbutton");
    await user.type(quantityInput, "0");
    await user.type(priceInput, "100");
    await user.click(screen.getByRole("button", { name: /save transaction/i }));

    expect(await screen.findByText(/must be greater than zero/i)).toBeInTheDocument();
  });

  it("opens Add Asset from the ticker picker and selects the newly-created asset", async () => {
    const user = userEvent.setup();
    // The real backend's GET /api/assets would include a just-created asset
    // on the next fetch (the mutation invalidates the ["assets"] query) --
    // the static default handler doesn't, so make it stateful for this test.
    let assets: Asset[] = [
      {
        id: 1,
        ticker: "3653",
        name: "健策",
        asset_type: "STOCK",
        market: "TWSE",
        currency: "TWD",
        sector: "Technology",
        industry: "Semiconductor Packaging",
        valuation_method: "TRANSACTION_BASED",
        is_demo_data: true,
        needs_review: false,
      },
    ];
    server.use(
      http.get(`${API_URL}/api/assets`, () => HttpResponse.json(assets)),
      http.get(`${API_URL}/api/assets/lookup/:ticker`, ({ params }) =>
        HttpResponse.json({
          ticker: params.ticker,
          name: "台積電",
          asset_type: "STOCK",
          market: "TWSE",
          sector: null,
          industry: null,
        }),
      ),
      http.post(`${API_URL}/api/assets/quick-create`, async ({ request }) => {
        const body = (await request.json()) as { ticker: string };
        const created: Asset = {
          id: 99,
          ticker: body.ticker,
          name: "台積電",
          asset_type: "STOCK",
          market: "TWSE",
          currency: "TWD",
          sector: null,
          industry: null,
          valuation_method: "TRANSACTION_BASED",
          is_demo_data: false,
          needs_review: false,
        };
        assets = [...assets, created];
        return HttpResponse.json(created, { status: 201 });
      }),
    );
    renderWithProviders(<Transactions />);

    await user.click(await screen.findByRole("button", { name: /add transaction/i }));
    await user.click(await screen.findByRole("button", { name: /找不到股票/ }));
    expect(screen.getByRole("heading", { name: /^add asset$/i })).toBeInTheDocument();

    await user.type(screen.getByLabelText(/股票代碼/), "2330");
    await screen.findByText(/已自動查到：台積電/, {}, { timeout: 2000 });
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: /^add asset$/i })).not.toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("combobox", { name: /asset/i })).toHaveValue("99"));
  });

  it("shows an error state when the transaction list request fails", async () => {
    server.use(http.get(`${API_URL}/api/transactions`, () => HttpResponse.json({ detail: "db down" }, { status: 500 })));
    renderWithProviders(<Transactions />);
    expect(await screen.findByText("db down")).toBeInTheDocument();
  });

  it("surfaces a failed delete instead of silently doing nothing", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API_URL}/api/transactions`, () =>
        HttpResponse.json([
          {
            id: 3,
            account_id: 1,
            asset_id: 1,
            date: "2026-05-20",
            type: "BUY",
            quantity: "10.0000",
            price: "640.0000",
            fee: "0.00",
            tax: "0.00",
            currency: "TWD",
            note: null,
            created_at: "2026-08-31T00:00:00",
          },
        ]),
      ),
      http.delete(`${API_URL}/api/transactions/3`, () =>
        HttpResponse.json({ detail: "Deleting this would leave a later SELL short 5.0000 shares." }, { status: 400 }),
      ),
    );
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithProviders(<Transactions />);

    await user.click(await screen.findByRole("button", { name: /delete/i }));

    expect(await screen.findByText(/would leave a later sell short/i)).toBeInTheDocument();
    confirmSpy.mockRestore();
  });
});
