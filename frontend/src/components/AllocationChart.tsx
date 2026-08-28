import Decimal from "decimal.js";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { AllocationEntry } from "../types/api";
import { formatCurrency, formatPercent } from "../utils/decimal";

const COLORS = ["#2563eb", "#16a34a", "#d97706", "#7c3aed", "#db2777", "#0891b2", "#65a30d", "#dc2626", "#4338ca", "#0f766e"];

interface AllocationChartProps {
  entries: AllocationEntry[];
}

export function AllocationChart({ entries }: AllocationChartProps) {
  const data = entries
    .filter((e) => new Decimal(e.market_value).gt(0))
    .map((e) => ({
      name: e.ticker,
      value: Number(new Decimal(e.market_value).toFixed(2)), // display-only: chart geometry, not a financial computation
      marketValue: e.market_value,
      weight: e.weight,
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={64} outerRadius={100} paddingAngle={1}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(_value, _name, item) => {
            const point = item.payload as (typeof data)[number];
            return [`${formatCurrency(point.marketValue)} (${formatPercent(point.weight, 1)})`, point.name];
          }}
        />
        <Legend verticalAlign="bottom" height={36} iconSize={8} wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
