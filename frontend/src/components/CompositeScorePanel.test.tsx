import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Score } from "../types/api";
import { CompositeScorePanel } from "./CompositeScorePanel";

function score(overrides: Partial<Score> = {}): Score {
  return {
    date: "2026-08-28",
    value_score: "80.00",
    growth_score: "70.00",
    momentum_score: "90.00",
    quality_score: "60.00",
    composite_score: "77.00",
    regime: "BULL",
    missing_components: [],
    source: "CALCULATED",
    ...overrides,
  };
}

describe("CompositeScorePanel", () => {
  it("shows an honest empty state when no score has been computed yet", () => {
    render(<CompositeScorePanel score={null} history={[]} />);
    expect(screen.getByText(/no composite score computed yet/i)).toBeInTheDocument();
  });

  it("renders the composite value, regime badge, and every sub-score", () => {
    render(<CompositeScorePanel score={score()} history={[]} />);
    expect(screen.getByText("77.0")).toBeInTheDocument();
    expect(screen.getByText("BULL")).toBeInTheDocument();
    expect(screen.getByText("Value")).toBeInTheDocument();
    expect(screen.getByText("80.0")).toBeInTheDocument();
  });

  it("renders a null sub-score as an em dash, never a fabricated 0", () => {
    render(<CompositeScorePanel score={score({ growth_score: null })} history={[]} />);
    const label = screen.getByText("Growth");
    expect(label.nextElementSibling?.textContent).toBe("—");
  });

  it("lists missing_components in the footer when present", () => {
    render(<CompositeScorePanel score={score({ growth_score: null, missing_components: ["growth"] })} history={[]} />);
    expect(screen.getByText(/missing: growth/i)).toBeInTheDocument();
  });

  it("omits the missing-components note entirely when nothing is missing", () => {
    render(<CompositeScorePanel score={score()} history={[]} />);
    expect(screen.queryByText(/missing:/i)).not.toBeInTheDocument();
  });

  it("shows Regime unknown when regime is null rather than a blank badge", () => {
    render(<CompositeScorePanel score={score({ regime: null })} history={[]} />);
    expect(screen.getByText(/regime unknown/i)).toBeInTheDocument();
  });

  it("does not render a trend chart with fewer than 2 history points", () => {
    const { container } = render(<CompositeScorePanel score={score()} history={[score()]} />);
    expect(container.querySelector(".recharts-responsive-container")).not.toBeInTheDocument();
  });

  it("renders a trend chart with 2+ history points that have a composite score", () => {
    const history = [score({ date: "2026-08-27", composite_score: "70.00" }), score({ date: "2026-08-28" })];
    const { container } = render(<CompositeScorePanel score={score()} history={history} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });
});
