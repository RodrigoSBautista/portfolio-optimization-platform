import type { RebalanceCadence } from "../../api/types";
import { Collapsible } from "../../components/Collapsible";

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

interface Props {
  value: AdvancedSimOptions;
  onChange: (next: AdvancedSimOptions) => void;
}

export function AdvancedOptions({ value, onChange }: Props) {
  const set = <K extends keyof AdvancedSimOptions>(
    key: K,
    v: AdvancedSimOptions[K],
  ) => onChange({ ...value, [key]: v });

  return (
    <Collapsible title="Advanced options">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Rebalance">
          <select
            value={value.rebalance}
            onChange={(e) =>
              set("rebalance", e.target.value as AdvancedSimOptions["rebalance"])
            }
            className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
          >
            <option value="none">None</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="annually">Annually</option>
          </select>
        </Field>

        <Field label="Risk-free rate (%/yr)">
          <NumInput
            value={value.riskFreePct}
            step={0.25}
            min={0}
            onChange={(v) => set("riskFreePct", v)}
          />
        </Field>

        <Field label="Contribution escalation (%/yr)">
          <NumInput
            value={value.escalationPct}
            step={0.5}
            min={0}
            onChange={(v) => set("escalationPct", v)}
          />
        </Field>

        <Field label="Advisory fee (%/yr)">
          <NumInput
            value={value.annualFeePct}
            step={0.05}
            min={0}
            onChange={(v) => set("annualFeePct", v)}
          />
        </Field>

        <div className="sm:col-span-2 lg:col-span-1">
          <label className="mb-1 flex items-center gap-2 text-xs text-content-muted dark:text-content-dark-muted">
            <input
              type="checkbox"
              checked={value.inflationOn}
              onChange={(e) => set("inflationOn", e.target.checked)}
              className="h-4 w-4 accent-brand"
            />
            Show in today&apos;s dollars (inflation-adjusted)
          </label>
          <NumInput
            value={value.inflationPct}
            step={0.1}
            min={0}
            disabled={!value.inflationOn}
            onChange={(v) => set("inflationPct", v)}
            suffix="%/yr"
          />
        </div>
      </div>
    </Collapsible>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
        {label}
      </span>
      {children}
    </label>
  );
}

function NumInput({
  value,
  onChange,
  step = 1,
  min,
  disabled,
  suffix,
}: {
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  disabled?: boolean;
  suffix?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        value={value}
        step={step}
        min={min}
        disabled={disabled}
        onChange={(e) => {
          const n = Number(e.target.value);
          onChange(Number.isFinite(n) ? n : 0);
        }}
        className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand disabled:opacity-50 dark:border-edge-dark dark:bg-surface-dark-alt"
      />
      {suffix && (
        <span className="shrink-0 text-xs text-content-muted dark:text-content-dark-muted">
          {suffix}
        </span>
      )}
    </div>
  );
}
