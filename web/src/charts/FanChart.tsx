import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BandPoint, DateValuePoint } from "../api/types";
import { formatCurrency } from "../lib/format";
import { useChartTheme } from "../theme/useTheme";
import { ChartTooltip } from "./ChartTooltip";

interface Props {
  bands: BandPoint[];
  // Optional dashed line of cumulative contributions (cost basis).
  contributed?: DateValuePoint[] | null;
  height?: number;
}

// Recharts stacks Areas, so nested percentile bands are expressed as a floor
// (transparent) plus the width up to the next percentile. We precompute those
// widths per row and shade three graduated bands (p5–p95 lightest, p25–p75 mid,
// p50 as a solid line). Single-hue blue keeps it distinct from the green/red
// return semantics used elsewhere.
interface FanRow {
  date: string;
  lo: number; // p5 floor (transparent)
  wLoMid: number; // p5 -> p25
  wMid: number; // p25 -> p75
  wMidHi: number; // p75 -> p95
  p50: number;
  contributed?: number;
}

const BAND = "#1a73e8"; // brand blue

export function FanChart({ bands, contributed, height = 340 }: Props) {
  const ct = useChartTheme();

  const contribByDate = new Map<string, number>();
  for (const c of contributed ?? []) contribByDate.set(c.date, c.value);

  const data: FanRow[] = bands.map((b) => ({
    date: b.date,
    lo: b.p5,
    wLoMid: b.p25 - b.p5,
    wMid: b.p75 - b.p25,
    wMidHi: b.p95 - b.p75,
    p50: b.p50,
    contributed: contribByDate.get(b.date),
  }));

  const hasContributed = (contributed?.length ?? 0) > 0;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 text-xs text-content-muted dark:text-content-dark-muted">
        <LegendSwatch opacity={0.12} label="5–95th percentile" />
        <LegendSwatch opacity={0.28} label="25–75th percentile" />
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4" style={{ background: BAND }} />
          Median (50th)
        </span>
        {hasContributed && (
          <span className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-0 w-4 border-t-2 border-dashed"
              style={{ borderColor: ct.benchmark }}
            />
            Contributed
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height} className="min-h-[220px]">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
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
                labelledOnly
                labels={{
                  p50: "Median",
                  contributed: "Contributed",
                }}
              />
            }
          />
          {/* Transparent floor to lift the stacked bands to the p5 line. */}
          <Area
            dataKey="lo"
            stackId="fan"
            stroke="none"
            fill="none"
            isAnimationActive={false}
            activeDot={false}
          />
          <Area
            dataKey="wLoMid"
            stackId="fan"
            stroke="none"
            fill={BAND}
            fillOpacity={0.12}
            isAnimationActive={false}
            activeDot={false}
          />
          <Area
            dataKey="wMid"
            stackId="fan"
            stroke="none"
            fill={BAND}
            fillOpacity={0.28}
            isAnimationActive={false}
            activeDot={false}
          />
          <Area
            dataKey="wMidHi"
            stackId="fan"
            stroke="none"
            fill={BAND}
            fillOpacity={0.12}
            isAnimationActive={false}
            activeDot={false}
          />
          {hasContributed && (
            <Line
              type="monotone"
              dataKey="contributed"
              stroke={ct.benchmark}
              strokeWidth={1.25}
              strokeDasharray="4 3"
              dot={false}
              isAnimationActive={false}
              connectNulls
            />
          )}
          <Line
            type="monotone"
            dataKey="p50"
            stroke={BAND}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function LegendSwatch({ opacity, label }: { opacity: number; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block h-3 w-4 rounded-sm"
        style={{ background: BAND, opacity }}
      />
      {label}
    </span>
  );
}
