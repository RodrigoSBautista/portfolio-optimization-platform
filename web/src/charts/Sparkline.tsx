import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { trendColor } from "../theme/colors";

interface Props {
  values: number[];
  changePct: number; // drives green/red
  width?: number;
  height?: number;
}

// Tiny sparkline for the sidebar rows, colored green/red by the % change.
export function Sparkline({ values, changePct, height = 28 }: Props) {
  const color = trendColor(changePct);
  const data = values.map((v, i) => ({ i, v }));
  const id = `spark-${Math.round(changePct * 1000)}-${values.length}`;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${id})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
