interface Props {
  label: string;
  value: string;
  tone?: "up" | "down" | "neutral";
}

// A single KPI tile for the dashboard grid.
export function KpiCard({ label, value, tone = "neutral" }: Props) {
  const toneClass =
    tone === "up"
      ? "text-up"
      : tone === "down"
        ? "text-down"
        : "text-content dark:text-content-dark";
  return (
    <div className="rounded-lg border border-edge bg-surface-alt px-4 py-3 dark:border-edge-dark dark:bg-surface-dark-alt">
      <div className="text-xs text-content-muted dark:text-content-dark-muted">
        {label}
      </div>
      <div className={`mt-1 text-lg font-semibold tabular-nums ${toneClass}`}>
        {value}
      </div>
    </div>
  );
}
