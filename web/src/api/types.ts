// Typed mirror of the FastAPI contract (api/schemas.py).

export interface Token {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  username: string;
}

export interface Ticker {
  symbol: string;
  name: string;
}

export interface Holding {
  symbol: string;
  weight: number;
}

export type ContributionKind = "lump_sum" | "recurring";

export interface Contribution {
  kind: ContributionKind;
  amount: number;
  frequency?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface PortfolioSpec {
  name: string;
  benchmark_symbol: string;
  base_currency: string;
  holdings: Holding[];
  contributions: Contribution[];
}

export interface Portfolio extends PortfolioSpec {
  id: number;
}

export interface SeriesPoint {
  date: string;
  value: number;
  invested: number;
  benchmark: number | null;
}

// Metric values are preformatted strings, e.g. "12.3%".
export type MetricBlock = Record<string, string>;
export type Metrics = Record<string, MetricBlock>;

export interface SimulateRequest {
  spec: Omit<PortfolioSpec, "base_currency"> & { base_currency?: string };
  start: string;
  benchmark?: string;
}

export interface SimulateResponse {
  series: SeriesPoint[];
  metrics: Metrics;
  final_value: number;
  invested: number;
  gain_pct: number;
  dropped: string[];
  benchmark: string;
}

export type OptimizeMode = "allocate" | "select";

export const ALLOCATION_METHODS = [
  "Equal weight",
  "Risk parity",
  "Inverse-volatility",
  "Minimum-variance",
  "Hierarchical Risk Parity",
] as const;

export const SELECTION_METHODS = [
  "Low volatility",
  "Correlation clustering",
] as const;

export type AllocationMethod = (typeof ALLOCATION_METHODS)[number];
export type SelectionMethod = (typeof SELECTION_METHODS)[number];

export interface OptimizeRequest {
  mode: OptimizeMode;
  method: AllocationMethod;
  tickers?: string[];
  candidates?: string[];
  k?: number;
  selection_method?: SelectionMethod;
  lookback_years: number;
  max_weight?: number | null;
  benchmark: string;
}

export interface ComparisonPoint {
  date: string;
  suggested: number;
  equal_weight: number | null;
  benchmark: number | null;
}

export interface OptimizeResponse {
  selected: string[];
  suggested: Record<string, number>;
  baseline: Record<string, number>;
  comparison_series: ComparisonPoint[];
  metrics: Metrics;
}

// --- Compare (POST /api/compare) ---

export interface DateValuePoint {
  date: string;
  value: number;
}

export interface CompareResult {
  id: number;
  name: string;
  series: DateValuePoint[];
  final_value: number;
  invested: number;
  metrics: MetricBlock;
}

export interface CompareRequest {
  portfolio_ids: number[];
  start: string;
  benchmark: string;
}

export interface CompareResponse {
  results: CompareResult[];
  benchmark_series: DateValuePoint[] | null;
  benchmark_metrics: MetricBlock | null;
}

// --- Tracking (GET /api/portfolios/{id}/valuations, POST .../refresh) ---

export interface Valuation {
  date: string;
  market_value: number;
  benchmark_value: number | null;
}

export interface ValuationsResponse {
  valuations: Valuation[];
}

export interface RefreshRequest {
  start?: string;
}

export interface RefreshResponse {
  written: number;
}
