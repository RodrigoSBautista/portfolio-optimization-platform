import { formatCurrency } from "../lib/format";
import { useChartTheme } from "../theme/useTheme";

interface PayloadItem {
  dataKey: string;
  value: number | null;
  color?: string;
}

interface Props {
  active?: boolean;
  label?: string;
  payload?: PayloadItem[];
  labels: Record<string, string>; // dataKey -> display label
  // When true, only render payload items that have an entry in `labels`. Lets
  // charts with helper/stacked series (e.g. the fan chart's band widths) hide
  // those raw values from the tooltip.
  labelledOnly?: boolean;
}

// A theme-aware tooltip shared by the growth and comparison charts.
export function ChartTooltip({ active, label, payload, labels, labelledOnly }: Props) {
  const ct = useChartTheme();
  if (!active || !payload?.length) return null;
  return (
    <div
      className="min-w-[9rem] rounded-lg px-3 py-2 text-xs shadow-lg backdrop-blur-sm"
      style={{
        background: ct.tooltipBg,
        border: `1px solid ${ct.tooltipBorder}`,
        color: ct.tooltipText,
      }}
    >
      <div className="mb-1.5 font-semibold opacity-70">{label}</div>
      <div className="flex flex-col gap-1">
        {payload
          .filter((p) => p.value != null && (!labelledOnly || labels[p.dataKey]))
          .map((p) => (
            <div key={p.dataKey} className="flex items-center gap-2">
              <span
                className="inline-block h-2 w-2 shrink-0 rounded-full"
                style={{ background: p.color }}
              />
              <span className="opacity-80">{labels[p.dataKey] ?? p.dataKey}</span>
              <span className="ml-auto font-semibold tabular-nums">
                {formatCurrency(p.value as number)}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
