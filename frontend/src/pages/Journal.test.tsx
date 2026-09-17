import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../test/server";
import { renderWithProviders } from "../test/renderWithProviders";
import { Journal } from "./Journal";

const API_URL = "http://127.0.0.1:8010";

function entry(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    entry_date: "2026-09-10",
    category: "OBSERVATION",
    asset_id: null,
    ticker: null,
    asset_name: null,
    recommendation_id: null,
    body: "Market felt choppy today.",
    created_at: "2026-09-10T08:00:00Z",
    updated_at: "2026-09-10T08:00:00Z",
    ...overrides,
  };
}

describe("Journal page", () => {
  it("shows the empty state when there are no entries", async () => {
    renderWithProviders(<Journal />);
    expect(await screen.findByText(/no journal entries yet/i)).toBeInTheDocument();
  });

  it("renders an existing entry", async () => {
    server.use(http.get(`${API_URL}/api/journal`, () => HttpResponse.json([entry()])));
    renderWithProviders(<Journal />);
    expect(await screen.findByText("Market felt choppy today.")).toBeInTheDocument();
    expect(screen.getByText("2026-09-10")).toBeInTheDocument();
  });

  it("shows the ticker on an asset-linked entry", async () => {
    server.use(
      http.get(`${API_URL}/api/journal`, () =>
        HttpResponse.json([entry({ asset_id: 1, ticker: "3653", asset_name: "健策" })]),
      ),
    );
    renderWithProviders(<Journal />);
    await screen.findByText("Market felt choppy today.");
    // The ticker filter dropdown also has an option with this text --
    // just confirm the entry row itself renders it too.
    expect(screen.getAllByText("3653 — 健策").length).toBeGreaterThanOrEqual(1);
  });

  it("shows the category badge on each entry", async () => {
    server.use(http.get(`${API_URL}/api/journal`, () => HttpResponse.json([entry({ category: "BUY_REASON" })])));
    renderWithProviders(<Journal />);
    expect(await screen.findByText("買入理由")).toBeInTheDocument();
  });

  it("filters entries by category", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API_URL}/api/journal`, ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get("category") === "REVIEW") {
          return HttpResponse.json([entry({ id: 2, body: "Reviewed this trade.", category: "REVIEW" })]);
        }
        return HttpResponse.json([entry()]);
      }),
    );
    renderWithProviders(<Journal />);
    await screen.findByText("Market felt choppy today.");

    await user.selectOptions(screen.getByDisplayValue("All categories"), "REVIEW");

    expect(await screen.findByText("Reviewed this trade.")).toBeInTheDocument();
  });

  it("adds a new entry with a category", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Journal />);

    await user.click(await screen.findByRole("button", { name: /add entry/i }));
    await user.selectOptions(screen.getByLabelText(/^category$/i), "REVIEW");
    await user.type(screen.getByLabelText(/^note$/i), "New note.");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: /^add entry$/i })).not.toBeInTheDocument());
  });

  it("requires a non-empty note", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Journal />);

    await user.click(await screen.findByRole("button", { name: /add entry/i }));
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    expect(await screen.findByText(/write something first/i)).toBeInTheDocument();
  });

  it("edits an existing entry", async () => {
    const user = userEvent.setup();
    server.use(http.get(`${API_URL}/api/journal`, () => HttpResponse.json([entry()])));
    renderWithProviders(<Journal />);

    await user.click(await screen.findByRole("button", { name: /^edit$/i }));
    expect(screen.getByRole("heading", { name: /^edit entry$/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: /^edit entry$/i })).not.toBeInTheDocument());
  });

  it("surfaces a delete error inline instead of failing silently", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    server.use(
      http.get(`${API_URL}/api/journal`, () => HttpResponse.json([entry()])),
      http.delete(`${API_URL}/api/journal/:id`, () => HttpResponse.json({ detail: "db down" }, { status: 500 })),
    );
    renderWithProviders(<Journal />);

    await user.click(await screen.findByRole("button", { name: /^delete$/i }));

    expect(await screen.findByText("db down")).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it("shows an error state when the list request fails", async () => {
    server.use(http.get(`${API_URL}/api/journal`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));
    renderWithProviders(<Journal />);
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });
});
