import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useChartTheme } from "../theme/useTheme";

interface Props {
  suggested: Record<string, number>;
  baseline: Record<string, number>;
}

// Grouped bar chart: suggested weight vs equal-weight baseline per ticker.
export function WeightsBar({ suggested, baseline }: Props) {
  const ct = useChartTheme();
  const tickers = Object.keys(suggested);
  const data = tickers.map((t) => ({
    ticker: t,
    suggested: +(suggested[t] * 100).toFixed(2),
    equal: +((baseline[t] ?? 0) * 100).toFixed(2),
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(220, tickers.length * 26 + 60)}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
      >
        <CartesianGrid horizontal={false} stroke={ct.grid} />
        <XAxis
          type="number"
          tick={{ fill: ct.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: ct.grid }}
          tickFormatter={(v: number) => `${v}%`}
        />
        <YAxis
          type="category"
          dataKey="ticker"
          tick={{ fill: ct.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={56}
        />
        <Tooltip
          cursor={{ fill: ct.grid, opacity: 0.3 }}
          contentStyle={{
            background: ct.tooltipBg,
            border: `1px solid ${ct.tooltipBorder}`,
            color: ct.tooltipText,
            borderRadius: 6,
            fontSize: 12,
          }}
          formatter={(v) => `${v}%`}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: ct.axis }} />
        <Bar dataKey="suggested" name="Suggested" radius={[0, 3, 3, 0]}>
          {data.map((d) => (
            <Cell key={d.ticker} fill="#1a7f37" />
          ))}
        </Bar>
        <Bar dataKey="equal" name="Equal weight" radius={[0, 3, 3, 0]} fill="#9aa0a6" />
      </BarChart>
    </ResponsiveContainer>
  );
}
