import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { InstitutionalFlow } from "../types/api";
import { Count } from "./Money";

const UP_COLOR = "#16a34a";
const DOWN_COLOR = "#dc2626";

interface InstitutionalFlowPanelProps {
  flows: InstitutionalFlow[];
}

/** Institutional-investor (三大法人) flow -- 4 latest-day summary cards plus
 * a bidirectional bar chart of foreign net buying over the trailing rows
 * (kanpan's UI pattern, Integration Report Sec.7), fed directly from
 * already-computed backend fields -- no arithmetic happens in this file. */
export function InstitutionalFlowPanel({ flows }: InstitutionalFlowPanelProps) {
  if (flows.length === 0) {
    return <p className="text-sm text-slate-400">No institutional flow data ingested yet for this ticker.</p>;
  }

  const latest = flows[flows.length - 1];
  const recent = flows.slice(-20);
  const chartData = recent.map((f) => ({ date: f.date, net: f.foreign_net }));

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <FlowCard label="外資 Foreign" value={latest.foreign_net} />
        <FlowCard label="投信 Inv. Trust" value={latest.investment_trust_net} />
        <FlowCard label="自營商 Dealer" value={latest.dealer_net} />
        <FlowCard label="合計 Total" value={latest.total_net} />
      </div>

      {chartData.some((d) => d.net !== null) && (
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={24} />
            <YAxis tick={{ fontSize: 10 }} width={56} />
            <Tooltip
              formatter={(value) => [typeof value === "number" ? value.toLocaleString() : "—", "Foreign net"]}
            />
            <Bar dataKey="net">
              {chartData.map((d, i) => (
                <Cell key={i} fill={(d.net ?? 0) >= 0 ? UP_COLOR : DOWN_COLOR} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      <p className="text-xs text-slate-400">
        Foreign/investment-trust/dealer net shares, latest as of {latest.date}. Source: {latest.source}
      </p>
    </div>
  );
}

function FlowCard({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-sm font-semibold">
        <Count value={value} colorBySign />
      </p>
    </div>
  );
}
