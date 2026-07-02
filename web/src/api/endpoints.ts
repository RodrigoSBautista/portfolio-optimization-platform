// Thin typed wrappers over the FastAPI routes. No business logic here — the UI
// reads input, calls these, and renders the result.
import { api } from "./client";
import type {
  CompareRequest,
  CompareResponse,
  OptimizeRequest,
  OptimizeResponse,
  Portfolio,
  PortfolioSpec,
  RefreshRequest,
  RefreshResponse,
  SimulateRequest,
  SimulateResponse,
  Ticker,
  Token,
  User,
  ValuationsResponse,
} from "./types";

export async function signup(username: string, password: string): Promise<Token> {
  const { data } = await api.post<Token>("/api/auth/signup", { username, password });
  return data;
}

export async function login(username: string, password: string): Promise<Token> {
  const { data } = await api.post<Token>("/api/auth/login", { username, password });
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>("/api/auth/me");
  return data;
}

export async function fetchTickers(): Promise<Ticker[]> {
  const { data } = await api.get<Ticker[]>("/api/tickers");
  return data;
}

export async function fetchPortfolios(): Promise<Portfolio[]> {
  const { data } = await api.get<Portfolio[]>("/api/portfolios");
  return data;
}

export async function createPortfolio(spec: PortfolioSpec): Promise<Portfolio> {
  const { data } = await api.post<Portfolio>("/api/portfolios", spec);
  return data;
}

export async function deletePortfolio(id: number): Promise<void> {
  await api.delete(`/api/portfolios/${id}`);
}

export async function simulate(req: SimulateRequest): Promise<SimulateResponse> {
  const { data } = await api.post<SimulateResponse>("/api/simulate", req);
  return data;
}

export async function optimize(req: OptimizeRequest): Promise<OptimizeResponse> {
  const { data } = await api.post<OptimizeResponse>("/api/optimize", req);
  return data;
}

export async function compare(req: CompareRequest): Promise<CompareResponse> {
  const { data } = await api.post<CompareResponse>("/api/compare", req);
  return data;
}

export async function fetchValuations(id: number): Promise<ValuationsResponse> {
  const { data } = await api.get<ValuationsResponse>(
    `/api/portfolios/${id}/valuations`,
  );
  return data;
}

export async function refreshValuations(
  id: number,
  req: RefreshRequest = {},
): Promise<RefreshResponse> {
  const { data } = await api.post<RefreshResponse>(
    `/api/portfolios/${id}/refresh`,
    req,
  );
  return data;
}
