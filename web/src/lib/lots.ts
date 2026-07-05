// Helpers for lot-based (actual-purchases) portfolios. A spec is lot-based iff
// its `lots` array is non-empty; such specs describe an existing portfolio whose
// per-stock buy dates drive performance (holdings/contributions may be empty).
import type { PortfolioSpec } from "../api/types";

export function isLotBased(spec: Pick<PortfolioSpec, "lots">): boolean {
  return !!spec.lots && spec.lots.length > 0;
}

// Unique symbols in purchase order, deduped. Used for subtitles/labels when
// `holdings` is empty on a lot-based spec.
export function lotSymbols(spec: Pick<PortfolioSpec, "lots">): string[] {
  if (!spec.lots) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const lot of spec.lots) {
    if (!seen.has(lot.symbol)) {
      seen.add(lot.symbol);
      out.push(lot.symbol);
    }
  }
  return out;
}

// The earliest purchase date (YYYY-MM-DD) across all lots, or null when none.
export function firstPurchaseDate(spec: Pick<PortfolioSpec, "lots">): string | null {
  if (!spec.lots || spec.lots.length === 0) return null;
  return spec.lots.reduce(
    (min, lot) => (lot.date < min ? lot.date : min),
    spec.lots[0].date,
  );
}

// The symbol list a UI should display for a spec: holdings when present, else
// the lot symbols. Falls back to an empty array.
export function displaySymbols(
  spec: Pick<PortfolioSpec, "holdings" | "lots">,
): string[] {
  if (spec.holdings && spec.holdings.length > 0) {
    return spec.holdings.map((h) => h.symbol);
  }
  return lotSymbols(spec);
}
