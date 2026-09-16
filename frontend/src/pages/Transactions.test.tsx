import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
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
