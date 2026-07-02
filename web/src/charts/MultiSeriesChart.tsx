import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DateValuePoint } from "../api/types";
import { formatCurrency } from "../lib/format";
import { seriesColor } from "../theme/colors";
import { useChartTheme } from "../theme/useTheme";
import { ChartTooltip } from "./ChartTooltip";

export interface NamedSeries {
  key: string; // stable dataKey used by recharts
  label: string; // display label
  points: DateValuePoint[];
}

interface Props {
  series: NamedSeries[];
  // Optional benchmark, drawn as a dashed neutral line.
  benchmark?: { label: string; points: DateValuePoint[] } | null;
  height?: number;
}

// Merge multiple {date,value} series into recharts rows keyed by date. Union of
// all dates, sorted; each series contributes its value under its `key`.
function mergeByDate(
  series: NamedSeries[],
  benchmark?: { points: DateValuePoint[] } | null,
): Record<string, number | string>[] {
  const rows = new Map<string, Record<string, number | string>>();
  const put = (date: string, key: string, value: number) => {
    const row = rows.get(date) ?? { date };
    row[key] = value;
    rows.set(date, row);
  };
  for (const s of series) for (const p of s.points) put(p.date, s.key, p.value);
  if (benchmark) for (const p of benchmark.points) put(p.date, "benchmark", p.value);
  return [...rows.values()].sort((a, b) =>
    String(a.date).localeCompare(String(b.date)),
  );
}

// One multi-line comparison chart: a distinct color per series + a dashed
// neutral benchmark line. Shares the theme-aware ChartTooltip.
export function MultiSeriesChart({ series, benchmark, height = 340 }: Props) {
  const ct = useChartTheme();
  const data = mergeByDate(series, benchmark);

  const labels: Record<string, string> = {};
  for (const s of series) labels[s.key] = s.label;
  if (benchmark) labels.benchmark = benchmark.label;

  return (
    <ResponsiveContainer width="100%" height={height} className="min-h-[220px]">
      <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
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
        <Tooltip content={<ChartTooltip labels={labels} />} />
        {benchmark && (
          <Line
            type="monotone"
            dataKey="benchmark"
            stroke={ct.benchmark}
            strokeWidth={1.25}
            strokeDasharray="4 3"
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
        )}
        {series.map((s, i) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            stroke={seriesColor(i)}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
