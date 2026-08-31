import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

// jsdom has no ResizeObserver -- PriceChart (lightweight-charts) uses one to
// keep the chart width in sync with its container. Tests mock the
// lightweight-charts module itself, but this component's own `new
// ResizeObserver(...)` call is real code, not part of that mock, so it
// still needs a global to exist.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub;

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
