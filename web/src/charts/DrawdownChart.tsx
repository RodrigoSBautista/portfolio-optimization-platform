import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DrawdownPoint } from "../api/types";
import { DOWN } from "../theme/colors";
import { useChartTheme } from "../theme/useTheme";

interface Props {
  points: DrawdownPoint[];
  height?: number;
}

// Underwater (drawdown) chart: the decline from each prior peak, always <= 0, so
// 0 sits at the TOP and troughs hang below it. Red fill signals loss, matching
// the down/negative semantics used across the app. `pct` is a fraction (e.g.
// -0.35 = -35%).
export function DrawdownChart({ points, height = 220 }: Props) {
  const ct = useChartTheme();
  const gradId = "drawdownFill";

  return (
    <ResponsiveContainer width="100%" height={height} className="min-h-[160px]">
      <AreaChart data={points} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={DOWN} stopOpacity={0.05} />
            <stop offset="100%" stopColor={DOWN} stopOpacity={0.4} />
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
          width={56}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          domain={["auto", 0]}
        />
        <Tooltip
          cursor={{ stroke: ct.grid }}
          contentStyle={{
            background: ct.tooltipBg,
            border: `1px solid ${ct.tooltipBorder}`,
            color: ct.tooltipText,
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(v) => [`${(Number(v) * 100).toFixed(1)}%`, "Drawdown"]}
        />
        <Area
          type="monotone"
          dataKey="pct"
          stroke={DOWN}
          strokeWidth={1.5}
          fill={`url(#${gradId})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
