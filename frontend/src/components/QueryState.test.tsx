import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiRequestError } from "../services/api";
import { QueryState } from "./QueryState";

describe("QueryState", () => {
  it("shows a loading indicator while loading", () => {
    render(
      <QueryState isLoading isError={false} error={undefined} data={undefined}>
        {() => <div>content</div>}
      </QueryState>,
    );
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("surfaces the backend's error message, not a generic one", () => {
    render(
      <QueryState
        isLoading={false}
        isError
        error={new ApiRequestError(400, "Cannot sell 999 units: only 3 available.")}
        data={undefined}
      >
        {() => <div>content</div>}
      </QueryState>,
    );
    expect(screen.getByText(/cannot sell 999 units/i)).toBeInTheDocument();
  });

  it("falls back to a generic message for a non-API error", () => {
    render(
      <QueryState isLoading={false} isError error={new Error("network down")} data={undefined}>
        {() => <div>content</div>}
      </QueryState>,
    );
    expect(screen.getByText(/couldn't load this/i)).toBeInTheDocument();
  });

  it("shows the empty state when isEmpty(data) is true", () => {
    render(
      <QueryState
        isLoading={false}
        isError={false}
        error={undefined}
        data={[] as string[]}
        isEmpty={(d) => d.length === 0}
        emptyTitle="Nothing yet."
        emptyHint="Add something."
      >
        {() => <div>content</div>}
      </QueryState>,
    );
    expect(screen.getByText("Nothing yet.")).toBeInTheDocument();
    expect(screen.getByText("Add something.")).toBeInTheDocument();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("renders children with the data when everything succeeds", () => {
    render(
      <QueryState isLoading={false} isError={false} error={undefined} data={["a"]} isEmpty={(d) => d.length === 0}>
        {(data) => <div>got {data.length} item</div>}
      </QueryState>,
    );
    expect(screen.getByText("got 1 item")).toBeInTheDocument();
  });
});
