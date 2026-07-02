import { useOutletContext } from "react-router-dom";
import type { Portfolio } from "../api/types";

// Context passed from the Layout to routed child views (shared portfolio
// selection + the New-portfolio / delete actions).
export interface ShellContext {
  portfolios: Portfolio[];
  selected: Portfolio | null;
  selectPortfolio: (p: Portfolio) => void;
  openNew: () => void;
  // Open the New-portfolio modal seeded from an optimization result.
  openNewSeeded: (weights: Record<string, number>, benchmark: string) => void;
  deletePortfolio: (p: Portfolio) => void;
}

export function useShell() {
  return useOutletContext<ShellContext>();
}
