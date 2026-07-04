import type { RebalanceCadence } from "../../api/types";

// Dashboard advanced simulation options. Defaults mirror the API contract's
// defaults (risk-free 4%, no inflation/rebalance, no escalation/fee).
export interface AdvancedSimOptions {
  rebalance: RebalanceCadence | "none";
  inflationOn: boolean;
  inflationPct: number; // annual %, default 2.5
  escalationPct: number; // contribution escalation %/yr
  annualFeePct: number; // advisory fee %/yr
  riskFreePct: number; // annual %, default 4
}

export const DEFAULT_ADVANCED: AdvancedSimOptions = {
  rebalance: "none",
  inflationOn: false,
  inflationPct: 2.5,
  escalationPct: 0,
  annualFeePct: 0,
  riskFreePct: 4,
};
