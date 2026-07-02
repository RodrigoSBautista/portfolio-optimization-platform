export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatSignedCurrency(value: number): string {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${formatCurrency(Math.abs(value))}`;
}

export function formatPct(value: number, digits = 1): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

// Tailwind text-color class by the sign of a value (green up / red down /
// neutral at exactly 0). Used for gain figures in tables and KPI columns.
export function seriesColorClass(value: number): string {
  if (value > 0) return "text-up";
  if (value < 0) return "text-down";
  return "";
}

// Parse the leading number out of a preformatted metric string (e.g. "23.3%",
// "-5.1%", "1.42") to recover its sign for green/red coloring. Returns 0 when no
// number can be parsed (neutral).
export function metricSign(formatted: string | undefined): number {
  if (!formatted) return 0;
  const match = formatted.match(/-?\d+(\.\d+)?/);
  if (!match) return 0;
  const n = Number(match[0]);
  return Number.isNaN(n) ? 0 : Math.sign(n);
}
