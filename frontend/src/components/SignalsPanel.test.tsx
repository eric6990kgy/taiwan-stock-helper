import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Signal, SignalResult } from "../types/api";
import { SignalsPanel } from "./SignalsPanel";

function signal(overrides: Partial<Signal> = {}): Signal {
  return {
    id: "PRICE_ABOVE_SMA20",
    category: "TECHNICAL",
    name: "股價站上20日均線",
    status: "BULLISH",
    value: "650.00",
    threshold: "630.00",
    as_of: "2026-08-28",
    explanation: "股價 650 站上 20 日均線 630.00",
    source: "CALCULATED",
    ...overrides,
  };
}

function result(overrides: Partial<SignalResult> = {}): SignalResult {
  return {
    ticker: "3653",
    as_of: "2026-08-28",
    overall_status: "BULLISH",
    composite_score: "70.00",
    regime: "BULL",
    signals: [signal()],
    ...overrides,
  };
}

describe("SignalsPanel", () => {
  it("renders the overall status badge and as-of date", () => {
    render(<SignalsPanel data={result()} />);
    expect(screen.getByText("Overall")).toBeInTheDocument();
    expect(screen.getByText("As of 2026-08-28")).toBeInTheDocument();
  });

  it("groups signals by category with a visible category label", () => {
    render(
      <SignalsPanel
        data={result({
          signals: [
            signal({ id: "PRICE_ABOVE_SMA20", category: "TECHNICAL" }),
            signal({ id: "FOREIGN_NET_BUYING", category: "INSTITUTIONAL", name: "外資買超" }),
          ],
        })}
      />,
    );
    expect(screen.getByText("Technical")).toBeInTheDocument();
    expect(screen.getByText("Institutional")).toBeInTheDocument();
  });

  it("renders each of BULLISH/BEARISH/NEUTRAL/UNAVAILABLE distinctly", () => {
    render(
      <SignalsPanel
        data={result({
          signals: [
            signal({ id: "A", status: "BULLISH", name: "Signal A" }),
            signal({ id: "B", status: "BEARISH", name: "Signal B" }),
            signal({ id: "C", status: "NEUTRAL", name: "Signal C" }),
            signal({ id: "D", status: "UNAVAILABLE", name: "Signal D" }),
          ],
        })}
      />,
    );
    expect(screen.getByText("Signal A").closest("button")?.textContent).toContain("BULLISH");
    expect(screen.getByText("Signal B").closest("button")?.textContent).toContain("BEARISH");
    expect(screen.getByText("Signal C").closest("button")?.textContent).toContain("NEUTRAL");
    expect(screen.getByText("Signal D").closest("button")?.textContent).toContain("UNAVAILABLE");
  });

  it("expands a signal row to show its explanation on click", () => {
    render(<SignalsPanel data={result()} />);
    expect(screen.queryByText(/股價 650 站上/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("股價站上20日均線"));
    expect(screen.getByText(/股價 650 站上/)).toBeInTheDocument();
  });

  it("never renders a signal's own status as BUY/SELL", () => {
    // The disclaimer paragraph legitimately mentions "buy/sell" while
    // explicitly disclaiming it -- what must never appear is a BUY/SELL
    // *status* badge on a signal itself.
    render(<SignalsPanel data={result()} />);
    for (const status of ["BUY", "SELL"]) {
      expect(screen.queryByText(status)).not.toBeInTheDocument();
    }
  });
});
