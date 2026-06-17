import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SeriesPoint } from "../api/types";
import { formatCurrency } from "../lib/format";
import { trendColor } from "../theme/colors";
import { useChartTheme } from "../theme/useTheme";
import { ChartTooltip } from "./ChartTooltip";

interface Props {
  series: SeriesPoint[];
  // Sign of the return that drives the trend color (>= 0 green, < 0 red).
  trendSign: number;
  benchmarkLabel: string;
}

// Large area growth chart: GREEN when the trend is >= 0, RED when < 0 (gradient
// fill + matching stroke). The benchmark is a thin neutral line.
export function GrowthChart({ series, trendSign, benchmarkLabel }: Props) {
  const ct = useChartTheme();
  const color = trendColor(trendSign);
  const hasBenchmark = series.some((p) => p.benchmark != null);
  const gradId = "growthFill";

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={series} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
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
          domain={["auto", "auto"]}
        />
        <Tooltip
          content={
            <ChartTooltip
              labels={{ value: "Value", invested: "Invested", benchmark: benchmarkLabel }}
            />
          }
        />
        {hasBenchmark && (
          <Line
            type="monotone"
            dataKey="benchmark"
            stroke={ct.benchmark}
            strokeWidth={1.25}
            strokeDasharray="4 3"
            dot={false}
            isAnimationActive={false}
          />
        )}
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          fill={`url(#${gradId})`}
          dot={false}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
