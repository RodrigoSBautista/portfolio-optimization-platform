import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import * as endpoints from "./endpoints";
import type {
  CompareRequest,
  OptimizeRequest,
  PortfolioSpec,
  RefreshRequest,
  SimulateRequest,
} from "./types";

export const keys = {
  tickers: ["tickers"] as const,
  portfolios: ["portfolios"] as const,
  valuations: (id: number) => ["valuations", id] as const,
};

export function useTickers() {
  return useQuery({
    queryKey: keys.tickers,
    queryFn: endpoints.fetchTickers,
    staleTime: Infinity, // the universe rarely changes within a session
  });
}

export function usePortfolios() {
  return useQuery({
    queryKey: keys.portfolios,
    queryFn: endpoints.fetchPortfolios,
  });
}

export function useCreatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (spec: PortfolioSpec) => endpoints.createPortfolio(spec),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.portfolios }),
  });
}

export function useDeletePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => endpoints.deletePortfolio(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.portfolios }),
  });
}

// Dashboard simulation. Keyed by the spec + start so range tabs re-fetch and cache.
export function useSimulation(req: SimulateRequest | null) {
  return useQuery({
    queryKey: ["simulate", req],
    queryFn: () => endpoints.simulate(req as SimulateRequest),
    enabled: !!req,
  });
}

export function useOptimize() {
  return useMutation({
    mutationFn: (req: OptimizeRequest) => endpoints.optimize(req),
  });
}

// Compare 2–3 saved portfolios. Keyed by the full request so range/benchmark/
// selection changes re-fetch and cache.
export function useCompare(req: CompareRequest | null) {
  return useQuery({
    queryKey: ["compare", req],
    queryFn: () => endpoints.compare(req as CompareRequest),
    enabled: !!req,
  });
}

// Stored valuation history for one portfolio (tracking dashboard).
export function useValuations(id: number | null) {
  return useQuery({
    queryKey: id != null ? keys.valuations(id) : ["valuations", "none"],
    queryFn: () => endpoints.fetchValuations(id as number),
    enabled: id != null,
  });
}

// Refresh (recompute + persist) a portfolio's valuations, then refetch them.
export function useRefreshValuations() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, req }: { id: number; req?: RefreshRequest }) =>
      endpoints.refreshValuations(id, req),
    onSuccess: (_data, { id }) =>
      qc.invalidateQueries({ queryKey: keys.valuations(id) }),
  });
}
