import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PricePoint } from "../types/api";
import { formatCurrency } from "../utils/decimal";

interface PriceChartProps {
  points: PricePoint[];
}

export function PriceChart({ points }: PriceChartProps) {
  // Chart rendering needs plain JS numbers for axis geometry -- display only,
  // never used for any P&L/cost-basis math (that stays in app.analytics).
  const data = points.map((p) => ({ date: p.date, close: Number(p.close), closeExact: p.close }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
        <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} width={56} />
        <Tooltip
          formatter={(_value, _name, item) => [formatCurrency((item.payload as { closeExact: string }).closeExact), "Close"]}
        />
        <Line type="monotone" dataKey="close" stroke="#2563eb" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
