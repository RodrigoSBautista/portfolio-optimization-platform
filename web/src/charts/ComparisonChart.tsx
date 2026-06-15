import {
  Area,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ComparisonPoint } from "../api/types";
import { formatCurrency } from "../lib/format";
import { UP } from "../theme/colors";
import { useChartTheme } from "../theme/useTheme";
import { ChartTooltip } from "./ChartTooltip";

interface Props {
  series: ComparisonPoint[];
  benchmarkLabel: string;
}

// Suggested (green area) vs equal-weight (blue line) vs benchmark (neutral line).
export function ComparisonChart({ series, benchmarkLabel }: Props) {
  const ct = useChartTheme();
  const labels = {
    suggested: "Suggested",
    equal_weight: "Equal weight",
    benchmark: benchmarkLabel,
  };
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={series} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="cmpFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={UP} stopOpacity={0.3} />
            <stop offset="100%" stopColor={UP} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{ fill: ct.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: ct.grid }}
          minTickGap={48}
        />
        <YAxis
          tick={{ fill: ct.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={64}
          tickFormatter={(v: number) => formatCurrency(v)}
        />
        <Tooltip content={<ChartTooltip labels={labels} />} />
        <Legend
          wrapperStyle={{ fontSize: 12, color: ct.axis }}
          formatter={(value: string) => labels[value as keyof typeof labels] ?? value}
        />
        <Line
          type="monotone"
          dataKey="benchmark"
          stroke={ct.benchmark}
          strokeWidth={1.25}
          strokeDasharray="4 3"
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="equal_weight"
          stroke="#1a73e8"
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
        <Area
          type="monotone"
          dataKey="suggested"
          stroke={UP}
          strokeWidth={2}
          fill="url(#cmpFill)"
          dot={false}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
