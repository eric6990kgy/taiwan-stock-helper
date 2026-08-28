import type { ThesisStatus, WatchlistStatus } from "../types/api";

export function DemoDataBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700 ring-1 ring-amber-200">
      Demo data
    </span>
  );
}

export function SnapshotBadge({ label = "Snapshot, not a time series" }: { label?: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500 ring-1 ring-slate-200">
      {label}
    </span>
  );
}

const WATCHLIST_STATUS_STYLES: Record<WatchlistStatus, string> = {
  WATCHING: "bg-slate-100 text-slate-600 ring-slate-200",
  RESEARCHING: "bg-blue-50 text-blue-700 ring-blue-200",
  CANDIDATE: "bg-amber-50 text-amber-700 ring-amber-200",
  OWNED: "bg-green-50 text-green-700 ring-green-200",
  REJECTED: "bg-red-50 text-red-600 ring-red-200",
};

export function WatchlistStatusBadge({ status }: { status: WatchlistStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${WATCHLIST_STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}

const THESIS_STATUS_STYLES: Record<ThesisStatus, string> = {
  INTACT: "bg-green-50 text-green-700 ring-green-200",
  NEEDS_REVIEW: "bg-amber-50 text-amber-700 ring-amber-200",
  BROKEN: "bg-red-50 text-red-600 ring-red-200",
};

export function ThesisStatusBadge({ status }: { status: ThesisStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${THESIS_STATUS_STYLES[status]}`}>
      {status.replace("_", " ")}
    </span>
  );
}
