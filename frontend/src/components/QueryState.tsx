import type { ReactNode } from "react";
import { ApiRequestError } from "../services/api";

interface QueryStateProps<T> {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  data: T | undefined;
  /** Return true to show the empty state instead of children -- e.g. an empty array. */
  isEmpty?: (data: T) => boolean;
  emptyTitle?: string;
  emptyHint?: string;
  loadingLabel?: string;
  children: (data: T) => ReactNode;
}

/** The one place loading / error / empty rendering is decided, so every
 * page looks and behaves the same way instead of five slightly different
 * ad hoc spinners (PRD Sec.40's empty-state copy pattern, applied uniformly). */
export function QueryState<T>({
  isLoading,
  isError,
  error,
  data,
  isEmpty,
  emptyTitle = "Nothing here yet.",
  emptyHint,
  loadingLabel = "Loading…",
  children,
}: QueryStateProps<T>) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-slate-200 bg-white py-16 text-sm text-slate-400">
        {loadingLabel}
      </div>
    );
  }

  if (isError) {
    const message = error instanceof ApiRequestError ? error.message : "Something went wrong loading this data.";
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-6 text-sm text-red-700">
        <p className="font-medium">Couldn't load this.</p>
        <p className="mt-1 text-red-600">{message}</p>
      </div>
    );
  }

  if (data === undefined) return null;

  if (isEmpty?.(data)) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white px-4 py-12 text-center">
        <p className="text-sm font-medium text-slate-600">{emptyTitle}</p>
        {emptyHint && <p className="mt-1 text-xs text-slate-400">{emptyHint}</p>}
      </div>
    );
  }

  return <>{children(data)}</>;
}
