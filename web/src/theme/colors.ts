// Centralized chart palette. UP/DOWN are theme-INDEPENDENT (green-up / red-down
// must read in both light and dark). Axis/grid/text colors adapt to the theme.

export const UP = "#1a7f37"; // green
export const DOWN = "#d1242f"; // red

export interface ChartTheme {
  axis: string; // axis tick labels
  grid: string; // gridlines
  benchmark: string; // benchmark series line
  tooltipBg: string;
  tooltipBorder: string;
  tooltipText: string;
}

export const LIGHT_CHART: ChartTheme = {
  axis: "#5f6368",
  grid: "#e8eaed",
  benchmark: "#5f6368",
  tooltipBg: "#ffffff",
  tooltipBorder: "#dadce0",
  tooltipText: "#202124",
};

export const DARK_CHART: ChartTheme = {
  axis: "#9aa0a6",
  grid: "#3c4043",
  benchmark: "#9aa0a6",
  tooltipBg: "#2a2b2e",
  tooltipBorder: "#3c4043",
  tooltipText: "#e8eaed",
};

// Pick stroke + a gradient pair based on the sign of a return.
export function trendColor(gainPct: number): string {
  return gainPct >= 0 ? UP : DOWN;
}
