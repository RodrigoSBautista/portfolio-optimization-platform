import { useMemo, useState } from "react";
import {
  Area,
  ComposedChart,
  Line,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BuyMarker, SeriesPoint } from "../api/types";
import { formatCurrency } from "../lib/format";
import { trendColor } from "../theme/colors";
import { useChartTheme } from "../theme/useTheme";
import { ChartTooltip } from "./ChartTooltip";

// Buy-date markers use purple — a categorical accent that avoids the chart's
// green/red return semantics, the blue "invested" line, and the gray benchmark.
const MARKER_COLOR = "#9334e6";
// Above this many markers we keep the dots but drop the per-dot text labels to
// avoid clutter (the amount/symbol is still in each dot's hover tooltip).
const MARKER_LABEL_LIMIT = 12;

interface Props {
  series: SeriesPoint[];
  // Sign of the return that drives the trend color (>= 0 green, < 0 red).
  trendSign: number;
  benchmarkLabel: string;
  // Which value field to plot for the main area. Defaults to nominal "value";
  // pass "real_value" to show inflation-adjusted "today's dollars".
  valueKey?: "value" | "real_value";
  valueLabel?: string;
  // Lot-based specs only: dated purchases to mark on the value line.
  buyMarkers?: BuyMarker[] | null;
}

interface MarkerDot {
  date: string;
  y: number;
  entries: BuyMarker[];
}

// Large area growth chart: GREEN when the trend is >= 0, RED when < 0 (gradient
// fill + matching stroke). Legend CHIPS above the chart toggle the benchmark and
// the invested (cost-basis) series on/off.
export function GrowthChart({
  series,
  trendSign,
  benchmarkLabel,
  valueKey = "value",
  valueLabel = "Value",
  buyMarkers,
}: Props) {
  const ct = useChartTheme();
  const color = trendColor(trendSign);
  const hasBenchmark = series.some((p) => p.benchmark != null);
  const gradId = "growthFill";

  const [showBenchmark, setShowBenchmark] = useState(true);
  const [showInvested, setShowInvested] = useState(false);

  const investedColor = "#1a73e8"; // brand blue

  // Snap each purchase to its point on the plotted value line, grouping buys on
  // the same date into one dot. Markers whose date isn't in the plotted window
  // are dropped (keeps the overlay honest).
  const markerDots = useMemo<MarkerDot[]>(() => {
    if (!buyMarkers?.length) return [];
    const valueByDate = new Map<string, number>();
    for (const p of series) {
      const v = p[valueKey];
      if (v != null) valueByDate.set(p.date, v);
    }
    const byDate = new Map<string, BuyMarker[]>();
    for (const m of buyMarkers) {
      const arr = byDate.get(m.date);
      if (arr) arr.push(m);
      else byDate.set(m.date, [m]);
    }
    const dots: MarkerDot[] = [];
    for (const [date, entries] of byDate) {
      const y = valueByDate.get(date);
      if (y != null) dots.push({ date, y, entries });
    }
    return dots;
  }, [buyMarkers, series, valueKey]);

  const showMarkerLabels = markerDots.length <= MARKER_LABEL_LIMIT;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        <LegendChip color={color} label={valueLabel} active disabled />
        <LegendChip
          color={investedColor}
          label="Invested"
          active={showInvested}
          onClick={() => setShowInvested((v) => !v)}
        />
        {hasBenchmark && (
          <LegendChip
            color={ct.benchmark}
            label={benchmarkLabel}
            dashed
            active={showBenchmark}
            onClick={() => setShowBenchmark((v) => !v)}
          />
        )}
        {markerDots.length > 0 && (
          <LegendChip color={MARKER_COLOR} label="Purchases" active disabled />
        )}
      </div>

      <ResponsiveContainer width="100%" height={340} className="min-h-[220px]">
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
                labels={{
                  [valueKey]: valueLabel,
                  invested: "Invested",
                  benchmark: benchmarkLabel,
                }}
              />
            }
          />
          {showInvested && (
            <Line
              type="stepAfter"
              dataKey="invested"
              stroke={investedColor}
              strokeWidth={1.25}
              dot={false}
              isAnimationActive={false}
            />
          )}
          {hasBenchmark && showBenchmark && (
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
            dataKey={valueKey}
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradId})`}
            dot={false}
            isAnimationActive={false}
          />
          {markerDots.map((d) => {
            const title =
              "Bought " +
              d.entries
                .map((e) => `${formatCurrency(e.amount)} of ${e.symbol}`)
                .join(", ");
            const symbols = [...new Set(d.entries.map((e) => e.symbol))].join("+");
            return (
              <ReferenceDot
                key={d.date}
                x={d.date}
                y={d.y}
                ifOverflow="extendDomain"
                // Native SVG <title> gives a no-JS, reduced-motion-safe hover
                // tooltip ("Bought $2,000 of NVDA").
                shape={(props) =>
                  props.cx == null || props.cy == null ? (
                    <circle r={0} />
                  ) : (
                    <circle
                      cx={props.cx}
                      cy={props.cy}
                      r={5}
                      fill={MARKER_COLOR}
                      stroke="#fff"
                      strokeWidth={1.5}
                    >
                      <title>{title}</title>
                    </circle>
                  )
                }
                label={
                  showMarkerLabels
                    ? {
                        value: symbols,
                        position: "top",
                        fill: MARKER_COLOR,
                        fontSize: 10,
                        fontWeight: 600,
                      }
                    : undefined
                }
              />
            );
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// A toggle chip that shows the series color swatch + label. The "Value" chip is
// disabled (always on); the others toggle their series.
function LegendChip({
  color,
  label,
  active = true,
  dashed = false,
  disabled = false,
  onClick,
}: {
  color: string;
  label: string;
  active?: boolean;
  dashed?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
        active
          ? "border-edge bg-surface-alt text-content dark:border-edge-dark dark:bg-surface-dark-alt dark:text-content-dark"
          : "border-edge/60 text-content-muted opacity-60 dark:border-edge-dark/60 dark:text-content-dark-muted"
      } ${disabled ? "cursor-default" : "hover:opacity-100"}`}
    >
      <span
        className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
        style={
          dashed
            ? { border: `1.5px dashed ${color}`, background: "transparent" }
            : { background: color }
        }
      />
      {label}
    </button>
  );
}
