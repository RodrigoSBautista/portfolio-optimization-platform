import {
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { FrontierResponse } from "../api/types";
import { seriesColor } from "../theme/colors";
import { useChartTheme } from "../theme/useTheme";

interface Props {
  data: FrontierResponse;
  height?: number;
}

// Efficient frontier in risk-return space: a light grey CLOUD of random
// portfolios, the frontier LINE, and labeled MARKERS (Equal weight + any
// suggested allocation). x = annualized volatility, y = annualized return, both
// fractions rendered as %.
export function FrontierChart({ data, height = 400 }: Props) {
  const ct = useChartTheme();
  const pct = (v: number) => `${(v * 100).toFixed(0)}%`;

  // Frontier points sorted by vol so the connecting line reads left-to-right.
  const frontier = [...data.frontier].sort((a, b) => a.vol - b.vol);
  const markers = data.markers;

  return (
    <ResponsiveContainer width="100%" height={height} className="min-h-[280px]">
      <ScatterChart margin={{ top: 12, right: 24, left: 12, bottom: 24 }}>
        <CartesianGrid stroke={ct.grid} />
        <XAxis
          type="number"
          dataKey="vol"
          name="Volatility"
          tick={{ fill: ct.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: ct.grid }}
          tickFormatter={pct}
          domain={["auto", "auto"]}
          label={{
            value: "Volatility (annualized)",
            position: "insideBottom",
            offset: -12,
            style: { fill: ct.axis, fontSize: 11, textAnchor: "middle" },
          }}
        />
        <YAxis
          type="number"
          dataKey="ret"
          name="Return"
          tick={{ fill: ct.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={pct}
          domain={["auto", "auto"]}
          width={56}
          label={{
            value: "Return (annualized)",
            angle: -90,
            position: "insideLeft",
            style: { fill: ct.axis, fontSize: 11, textAnchor: "middle" },
          }}
        />
        <ZAxis range={[40, 40]} />
        <Tooltip
          cursor={{ stroke: ct.grid }}
          contentStyle={{
            background: ct.tooltipBg,
            border: `1px solid ${ct.tooltipBorder}`,
            color: ct.tooltipText,
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(v) => pct(Number(v))}
        />

        {/* Random-portfolio cloud (small, low-contrast dots). */}
        <Scatter
          name="Random portfolios"
          data={data.cloud}
          fill={ct.axis}
          fillOpacity={0.25}
          isAnimationActive={false}
        />

        {/* Frontier line: connect the sorted frontier points. */}
        <Scatter
          name="Efficient frontier"
          data={frontier}
          line={{ stroke: "#1a73e8", strokeWidth: 2 }}
          lineJointType="monotoneX"
          fill="#1a73e8"
          isAnimationActive={false}
        />

        {/* Labeled markers (Equal weight + suggested), one color each. */}
        <Scatter
          name="Markers"
          data={markers}
          isAnimationActive={false}
          shape="star"
        >
          {markers.map((m, i) => (
            <Cell key={m.label} fill={seriesColor(i)} />
          ))}
          <LabelList
            dataKey="label"
            position="top"
            style={{ fill: ct.tooltipText, fontSize: 11, fontWeight: 600 }}
          />
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
