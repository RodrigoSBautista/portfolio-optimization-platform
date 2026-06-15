import type { PortfolioSpec } from "../api/types";

// Single-holding specs used to render benchmark-index rows in the sidebar. These
// are not saved portfolios — just a quick simulate to get a sparkline.
export interface BenchmarkIndex {
  symbol: string;
  name: string;
  spec: PortfolioSpec;
}

function indexSpec(symbol: string, name: string): PortfolioSpec {
  return {
    name,
    benchmark_symbol: "SPY",
    base_currency: "USD",
    holdings: [{ symbol, weight: 1 }],
    contributions: [],
  };
}

export const BENCHMARK_INDICES: BenchmarkIndex[] = [
  { symbol: "SPY", name: "S&P 500 (SPY)", spec: indexSpec("SPY", "S&P 500 (SPY)") },
  { symbol: "QQQ", name: "Nasdaq 100 (QQQ)", spec: indexSpec("QQQ", "Nasdaq 100 (QQQ)") },
];
