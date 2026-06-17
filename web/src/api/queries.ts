import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import * as endpoints from "./endpoints";
import type {
  OptimizeRequest,
  PortfolioSpec,
  SimulateRequest,
} from "./types";

export const keys = {
  tickers: ["tickers"] as const,
  portfolios: ["portfolios"] as const,
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
