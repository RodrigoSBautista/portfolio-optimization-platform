import { useSparkline } from "../api/useSparkline";
import type { PortfolioSpec } from "../api/types";
import { Sparkline } from "../charts/Sparkline";
import { formatPct } from "../lib/format";

interface Props {
  id: string | number;
  label: string;
  sublabel?: string;
  spec: PortfolioSpec;
  active?: boolean;
  onClick?: () => void;
}

// One sidebar entry: name + tiny sparkline + green/red % change (1Y, from simulate).
export function SidebarRow({ id, label, sublabel, spec, active, onClick }: Props) {
  const { data, isLoading } = useSparkline(spec, id);
  const change = data?.changePct ?? 0;
  const up = change >= 0;

  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-2 rounded-md px-2 py-2 text-left transition-colors ${
        active
          ? "bg-surface-alt dark:bg-surface-dark-alt"
          : "hover:bg-surface-alt dark:hover:bg-surface-dark-alt"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{label}</div>
        {sublabel && (
          <div className="truncate text-xs text-content-muted dark:text-content-dark-muted">
            {sublabel}
          </div>
        )}
      </div>
      <div className="h-7 w-16 shrink-0">
        {data && data.values.length > 1 && (
          <Sparkline values={data.values} changePct={change} />
        )}
      </div>
      <div
        className={`w-14 shrink-0 text-right text-xs tabular-nums ${
          up ? "text-up" : "text-down"
        }`}
      >
        {isLoading ? "…" : formatPct(change)}
      </div>
    </button>
  );
}
