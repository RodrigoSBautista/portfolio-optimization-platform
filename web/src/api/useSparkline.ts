import { useQuery } from "@tanstack/react-query";
import { simulate } from "./endpoints";
import type { PortfolioSpec } from "./types";
import { oneYearAgo } from "../lib/dates";

export interface SparkData {
  values: number[];
  changePct: number;
}

// Derives a ~1Y sparkline + % change (last vs first of the value series) for a
// spec, via /api/simulate. Used by the sidebar rows.
export function useSparkline(spec: PortfolioSpec, id: string | number) {
  // Hash the parts that affect the simulation so the cache refreshes after an
  // edit to holdings/contributions/benchmark (not just when the id changes).
  const specHash = JSON.stringify({
    holdings: spec.holdings,
    contributions: spec.contributions,
    benchmark: spec.benchmark_symbol,
  });
  return useQuery({
    queryKey: ["sparkline", id, specHash],
    queryFn: async (): Promise<SparkData> => {
      const res = await simulate({ spec, start: oneYearAgo() });
      const values = res.series.map((p) => p.value);
      const first = values.find((v) => v > 0) ?? 0;
      const last = values.length ? values[values.length - 1] : 0;
      const changePct = first > 0 ? (last / first - 1) * 100 : 0;
      return { values, changePct };
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
