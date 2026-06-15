import { useContext } from "react";
import { ThemeContext } from "./theme-context";
import { DARK_CHART, LIGHT_CHART, type ChartTheme } from "./colors";

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}

// Resolve the chart palette (axis/grid/tooltip colors) for the active theme.
export function useChartTheme(): ChartTheme {
  const { theme } = useTheme();
  return theme === "dark" ? DARK_CHART : LIGHT_CHART;
}
