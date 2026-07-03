import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RollingPoint } from "../api/types";
import { useChartTheme } from "../theme/useTheme";

interface Props {
  points: RollingPoint[];
  height?: number;
}

const RET_COLOR = "#1a73e8"; // blue
const VOL_COLOR = "#e8710a"; // orange

// Rolling 1-year return and volatility over time. Two clearly-labeled lines in
// distinct hues (blue/orange, colorblind-safe and off the green/red return
// semantics). Values are fractions (e.g. 0.12 = 12%). Nulls before a full
// window are skipped (connectNulls off so gaps read honestly).
export function RollingChart({ points, height = 220 }: Props) {
  const ct = useChartTheme();
  const pct = (v: number) => `${(v * 100).toFixed(0)}%`;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 text-xs text-content-muted dark:text-content-dark-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4" style={{ background: RET_COLOR }} />
          Rolling 1-yr return
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4" style={{ background: VOL_COLOR }} />
          Rolling 1-yr volatility
        </span>
      </div>
      <ResponsiveContainer width="100%" height={height} className="min-h-[160px]">
        <LineChart data={points} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
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
            tickFormatter={pct}
            domain={["auto", "auto"]}
          />
          <ReferenceLine y={0} stroke={ct.grid} />
          <Tooltip
            cursor={{ stroke: ct.grid }}
            contentStyle={{
              background: ct.tooltipBg,
              border: `1px solid ${ct.tooltipBorder}`,
              color: ct.tooltipText,
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(v, name) => [
              `${(Number(v) * 100).toFixed(1)}%`,
              name === "ret_1y" ? "Return (1y)" : "Volatility (1y)",
            ]}
          />
          <Line
            type="monotone"
            dataKey="ret_1y"
            stroke={RET_COLOR}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="vol_1y"
            stroke={VOL_COLOR}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
