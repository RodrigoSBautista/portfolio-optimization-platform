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
  // Present when the simulate request set `inflation_pct` — the portfolio value
  // expressed in "today's dollars".
  real_value?: number;
}

// Metric values are preformatted strings, e.g. "12.3%".
export type MetricBlock = Record<string, string>;
export type Metrics = Record<string, MetricBlock>;

export type RebalanceCadence = "monthly" | "quarterly" | "annually";

export interface SimulateRequest {
  spec: Omit<PortfolioSpec, "base_currency"> & { base_currency?: string };
  start: string;
  benchmark?: string;
  // --- Advanced options (all optional; the backend applies sensible defaults) ---
  end?: string | null;
  rebalance?: RebalanceCadence | null;
  risk_free_rate?: number; // annual fraction, default 0.04
  inflation_pct?: number | null; // annual %, e.g. 2.5
  escalation_pct?: number;
  annual_fee_pct?: number;
  include_analytics?: boolean;
}

// Underwater / drawdown point (pct <= 0).
export interface DrawdownPoint {
  date: string;
  pct: number;
}

// Rolling 1-year return / volatility (either may be null before a full window).
export interface RollingPoint {
  date: string;
  ret_1y: number | null;
  vol_1y: number | null;
}

export interface SimulateResponse {
  series: SeriesPoint[];
  metrics: Metrics;
  final_value: number;
  invested: number;
  gain_pct: number;
  dropped: string[];
  benchmark: string;
  // Present when the request set `inflation_pct`.
  real_final_value?: number | null;
  // Present when the request set `include_analytics`.
  drawdown?: DrawdownPoint[];
  rolling?: RollingPoint[];
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
  // Holdings excluded because they had no price data in the shared window.
  dropped: string[];
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

// --- Projection (POST /api/project) ---

// One percentile band point across the projection horizon.
export interface BandPoint {
  date: string;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
}

// Terminal (end-of-horizon) percentile summary.
export interface Percentiles {
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
}

export interface ProjectRequest {
  spec: PortfolioSpec;
  years: number;
  n_paths?: number;
  seed?: number;
  goal?: number | null;
  start_value: number;
  lookback_years?: number;
}

export interface ProjectResponse {
  bands: BandPoint[];
  terminal: Percentiles;
  // Cumulative contributed (cost-basis) line across the horizon.
  contributed: DateValuePoint[];
  goal_probability: number | null;
  caveat: string;
}

// --- Retirement (POST /api/retirement) ---

export type WithdrawalKind = "fixed" | "rate";

export interface Withdrawal {
  kind: WithdrawalKind;
  amount?: number; // fixed $/mo (grows with inflation)
  rate?: number; // annual withdrawal rate as a fraction, e.g. 0.04
}

export interface RetirementRequest {
  spec: PortfolioSpec;
  start_balance: number;
  years: number;
  withdrawal: Withdrawal;
  inflation_pct?: number;
  n_paths?: number;
  seed?: number;
  lookback_years?: number;
}

export interface RetirementResponse {
  success_rate: number;
  bands: BandPoint[];
  years_lasted: Percentiles;
  caveat: string;
}

// --- Efficient frontier (POST /api/frontier) ---

export interface FrontierExtraPoint {
  label: string;
  weights: Record<string, number>;
}

export interface FrontierRequest {
  tickers: string[];
  lookback_years?: number;
  n_samples?: number;
  seed?: number;
  risk_free_rate?: number;
  extra_points?: FrontierExtraPoint[];
}

// A vol/return point in risk-return space (annualized fractions).
export interface RiskReturnPoint {
  vol: number;
  ret: number;
}

export interface FrontierMarker extends RiskReturnPoint {
  label: string;
}

export interface FrontierResponse {
  cloud: RiskReturnPoint[];
  frontier: RiskReturnPoint[];
  markers: FrontierMarker[];
}

// --- Diversification (POST /api/diversification) ---

export interface CorrelationMatrix {
  tickers: string[];
  values: number[][];
}

export interface Cluster {
  label: string;
  members: string[];
}

export interface RiskContribution {
  ticker: string;
  pct: number; // fraction of total portfolio risk
}

export interface DiversificationRequest {
  tickers: string[];
  lookback_years?: number;
  weights?: Record<string, number>;
}

export interface DiversificationResponse {
  matrix: CorrelationMatrix;
  clusters: Cluster[];
  risk_contributions: RiskContribution[];
}
