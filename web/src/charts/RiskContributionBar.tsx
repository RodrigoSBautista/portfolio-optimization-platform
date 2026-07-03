import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RiskContribution } from "../api/types";
import { seriesColor } from "../theme/colors";
import { useChartTheme } from "../theme/useTheme";

interface Props {
  contributions: RiskContribution[];
  height?: number;
}

// Horizontal bars of each holding's share of total portfolio risk (largest at
// top). `pct` is a fraction; rendered as %.
export function RiskContributionBar({ contributions, height }: Props) {
  const ct = useChartTheme();
  const data = [...contributions]
    .sort((a, b) => b.pct - a.pct)
    .map((c) => ({ ticker: c.ticker, pct: +(c.pct * 100).toFixed(2) }));

  const h = height ?? Math.max(180, data.length * 30 + 48);

  return (
    <ResponsiveContainer width="100%" height={h} className="min-h-[160px]">
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 24, left: 8, bottom: 0 }}
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
          formatter={(v) => [`${Number(v)}%`, "Risk share"]}
        />
        <Bar dataKey="pct" name="Risk share" radius={[0, 3, 3, 0]}>
          {data.map((d, i) => (
            <Cell key={d.ticker} fill={seriesColor(i)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
