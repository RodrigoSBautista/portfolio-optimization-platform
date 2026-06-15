// Time-range tabs for the dashboard. Each maps to a `start` date (YYYY-MM-DD)
// that gets sent to /api/simulate.

export type RangeKey = "1M" | "6M" | "YTD" | "1Y" | "5Y" | "MAX";

export const RANGES: RangeKey[] = ["1M", "6M", "YTD", "1Y", "5Y", "MAX"];

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

// The earliest sensible start; MAX uses a long lookback that covers the dataset.
const MAX_START = "2010-01-01";

export function startForRange(range: RangeKey, today = new Date()): string {
  const d = new Date(today);
  switch (range) {
    case "1M":
      d.setMonth(d.getMonth() - 1);
      return iso(d);
    case "6M":
      d.setMonth(d.getMonth() - 6);
      return iso(d);
    case "YTD":
      return iso(new Date(today.getFullYear(), 0, 1));
    case "1Y":
      d.setFullYear(d.getFullYear() - 1);
      return iso(d);
    case "5Y":
      d.setFullYear(d.getFullYear() - 5);
      return iso(d);
    case "MAX":
      return MAX_START;
  }
}

export function oneYearAgo(today = new Date()): string {
  const d = new Date(today);
  d.setFullYear(d.getFullYear() - 1);
  return iso(d);
}
