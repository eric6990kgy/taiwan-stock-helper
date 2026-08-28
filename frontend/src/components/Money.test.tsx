import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Money, Percent, Shares } from "./Money";

describe("Money", () => {
  it("renders a decimal-safe formatted amount", () => {
    render(<Money value="135750.00000000" />);
    expect(screen.getByText("NT$135,750")).toBeInTheDocument();
  });

  it("colors negative values when colorBySign is set", () => {
    render(<Money value="-49514" colorBySign />);
    expect(screen.getByText("NT$-49,514").className).toContain("negative");
  });
});

describe("Percent", () => {
  it("renders a signed percentage and colors it by default", () => {
    render(<Percent value="0.0823" />);
    const el = screen.getByText("+8.23%");
    expect(el).toBeInTheDocument();
    expect(el.className).toContain("positive");
  });

  it("shows an em dash for a null return (never a fake 0%)", () => {
    render(<Percent value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("Shares", () => {
  it("trims the API's fixed-scale trailing zeros", () => {
    render(<Shares value="15.0000" />);
    expect(screen.getByText("15")).toBeInTheDocument();
  });
});
