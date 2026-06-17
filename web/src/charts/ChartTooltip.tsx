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
}

// A theme-aware tooltip shared by the growth and comparison charts.
export function ChartTooltip({ active, label, payload, labels }: Props) {
  const ct = useChartTheme();
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-md px-3 py-2 text-xs shadow-md"
      style={{
        background: ct.tooltipBg,
        border: `1px solid ${ct.tooltipBorder}`,
        color: ct.tooltipText,
      }}
    >
      <div className="mb-1 font-medium">{label}</div>
      {payload
        .filter((p) => p.value != null)
        .map((p) => (
          <div key={p.dataKey} className="flex items-center gap-2">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: p.color }}
            />
            <span className="opacity-80">{labels[p.dataKey] ?? p.dataKey}</span>
            <span className="ml-auto font-medium">
              {formatCurrency(p.value as number)}
            </span>
          </div>
        ))}
    </div>
  );
}
