import { screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
import { Dashboard } from "./Dashboard";

const API_URL = "http://127.0.0.1:8010";

describe("Dashboard", () => {
  it("renders the portfolio summary numbers from the API, decimal-exact", async () => {
    renderWithProviders(<Dashboard />);

    await waitFor(() => expect(screen.getByText("NT$135,750")).toBeInTheDocument());
    expect(screen.getByText("NT$185,264")).toBeInTheDocument(); // remaining cost basis
    // total_return_pct = -0.26726... -> displayed as -26.73%, not a naive/wrong rounding.
    expect(screen.getByText("-26.73%")).toBeInTheDocument();
  });

  it("labels the performance section as a snapshot, not a time series", async () => {
    renderWithProviders(<Dashboard />);
    await waitFor(() => expect(screen.getByText(/snapshot, not a time series/i)).toBeInTheDocument());
  });

  it("shows the DEMO DATA badge", async () => {
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText(/demo data/i)).toBeInTheDocument();
  });

  it("renders holdings from the API in the table", async () => {
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText("3653")).toBeInTheDocument();
  });

  it("renders the watchlist widget", async () => {
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText("3491")).toBeInTheDocument();
  });

  it("shows an empty state when there are no holdings", async () => {
    server.use(http.get(`${API_URL}/api/holdings`, () => HttpResponse.json([])));
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText(/no holdings yet/i)).toBeInTheDocument();
  });

  it("shows an error state when the portfolio request fails", async () => {
    server.use(http.get(`${API_URL}/api/portfolio`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText(/couldn't load this/i)).toBeInTheDocument();
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });
});
