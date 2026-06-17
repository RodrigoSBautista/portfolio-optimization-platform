import { useState } from "react";
import { apiErrorMessage } from "../api/client";
import { useCreatePortfolio } from "../api/queries";
import type { Contribution, Portfolio, PortfolioSpec } from "../api/types";
import { TickerSearch } from "../components/TickerSearch";

interface Props {
  onCreated: (p: Portfolio) => void;
  onCancel: () => void;
  // When provided, seed the holdings (e.g. from the Optimize "Save as portfolio").
  initialWeights?: Record<string, number>;
  initialName?: string;
  initialBenchmark?: string;
}

type WeightMode = "weight" | "amount";
interface Row {
  symbol: string;
  amount: number; // interpreted per the active mode (weight fraction or $)
}

export function NewPortfolio({
  onCreated,
  onCancel,
  initialWeights,
  initialName,
  initialBenchmark,
}: Props) {
  const create = useCreatePortfolio();
  const [name, setName] = useState(initialName ?? "");
  const [benchmark, setBenchmark] = useState(initialBenchmark ?? "SPY");
  const [mode, setMode] = useState<WeightMode>("weight");
  const [rows, setRows] = useState<Row[]>(
    initialWeights
      ? Object.entries(initialWeights).map(([symbol, w]) => ({ symbol, amount: w }))
      : [],
  );

  // Contribution plan.
  const [lumpSum, setLumpSum] = useState(1000);
  const [recurring, setRecurring] = useState(0);
  const [frequency, setFrequency] = useState("monthly");

  const [error, setError] = useState<string | null>(null);

  function addRow(symbol: string) {
    if (rows.some((r) => r.symbol === symbol)) return;
    setRows([...rows, { symbol, amount: 0 }]);
  }
  function removeRow(symbol: string) {
    setRows(rows.filter((r) => r.symbol !== symbol));
  }
  function setAmount(symbol: string, value: number) {
    setRows(rows.map((r) => (r.symbol === symbol ? { ...r, amount: value } : r)));
  }

  const total = rows.reduce((s, r) => s + (r.amount || 0), 0);

  // Derive normalized weights (sum to 1) from rows under the active mode.
  function computeWeights(): Record<string, number> | null {
    if (rows.length === 0 || total <= 0) return null;
    const w: Record<string, number> = {};
    for (const r of rows) w[r.symbol] = (r.amount || 0) / total;
    return w;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const weights = computeWeights();
    if (!name.trim()) return setError("Give the portfolio a name.");
    if (!weights) return setError("Add at least one holding with a positive value.");

    // In $-amount mode the lump sum IS the sum of the per-ticker dollars (weights
    // still derive from the same amounts); the separate lump-sum field is ignored.
    const lump = mode === "amount" ? total : lumpSum;

    const contributions: Contribution[] = [];
    if (lump > 0) contributions.push({ kind: "lump_sum", amount: lump });
    if (recurring > 0)
      contributions.push({ kind: "recurring", amount: recurring, frequency });

    const spec: PortfolioSpec = {
      name: name.trim(),
      benchmark_symbol: benchmark.toUpperCase(),
      base_currency: "USD",
      holdings: Object.entries(weights).map(([symbol, weight]) => ({ symbol, weight })),
      contributions,
    };

    try {
      const created = await create.mutateAsync(spec);
      onCreated(created);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save the portfolio."));
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <label className="block">
        <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
          Name
        </span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My growth portfolio"
          className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
        />
      </label>

      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
            Benchmark
          </span>
          <input
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value)}
            className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
            Input mode
          </span>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as WeightMode)}
            className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
          >
            <option value="weight">Weights (relative)</option>
            <option value="amount">Dollar amounts</option>
          </select>
        </label>
      </div>

      <div>
        <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
          Add holdings
        </span>
        <TickerSearch
          onSelect={addRow}
          exclude={rows.map((r) => r.symbol)}
          placeholder="Search ticker to add…"
        />
      </div>

      {rows.length > 0 && (
        <div className="rounded-md border border-edge dark:border-edge-dark">
          {rows.map((r) => {
            const pct = total > 0 ? ((r.amount || 0) / total) * 100 : 0;
            return (
              <div
                key={r.symbol}
                className="flex items-center gap-3 border-b border-edge/60 px-3 py-2 last:border-b-0 dark:border-edge-dark/60"
              >
                <span className="w-16 text-sm font-medium">{r.symbol}</span>
                <input
                  type="number"
                  min={0}
                  step={mode === "weight" ? 0.1 : 100}
                  value={r.amount}
                  onChange={(e) => setAmount(r.symbol, Number(e.target.value))}
                  className="w-28 rounded-md border border-edge bg-surface px-2 py-1 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
                />
                <span className="w-14 text-right text-xs tabular-nums text-content-muted dark:text-content-dark-muted">
                  {pct.toFixed(1)}%
                </span>
                <button
                  type="button"
                  onClick={() => removeRow(r.symbol)}
                  className="ml-auto text-content-muted hover:text-down dark:text-content-dark-muted"
                  aria-label={`Remove ${r.symbol}`}
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}

      <fieldset className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <label className="block">
          <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
            {mode === "amount" ? "Lump sum ($, = total below)" : "Lump sum ($)"}
          </span>
          <input
            type="number"
            min={0}
            value={mode === "amount" ? total : lumpSum}
            onChange={(e) => setLumpSum(Number(e.target.value))}
            disabled={mode === "amount"}
            title={
              mode === "amount"
                ? "In dollar-amount mode the lump sum is the sum of the per-ticker amounts."
                : undefined
            }
            className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand disabled:opacity-50 dark:border-edge-dark dark:bg-surface-dark-alt"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
            Recurring ($)
          </span>
          <input
            type="number"
            min={0}
            value={recurring}
            onChange={(e) => setRecurring(Number(e.target.value))}
            className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
            Frequency
          </span>
          <select
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
            disabled={recurring <= 0}
            className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand disabled:opacity-50 dark:border-edge-dark dark:bg-surface-dark-alt"
          >
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="yearly">Yearly</option>
          </select>
        </label>
      </fieldset>

      {error && (
        <div className="rounded-md border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
          {error}
        </div>
      )}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-edge px-4 py-2 text-sm hover:bg-surface-alt dark:border-edge-dark dark:hover:bg-surface-dark-alt"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
        >
          {create.isPending ? "Saving…" : "Save portfolio"}
        </button>
      </div>
    </form>
  );
}
