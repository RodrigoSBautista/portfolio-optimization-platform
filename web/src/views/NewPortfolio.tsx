import { useRef, useState } from "react";
import { toast } from "sonner";
import { apiErrorMessage } from "../api/client";
import { useCreatePortfolio } from "../api/queries";
import type { Contribution, Lot, Portfolio, PortfolioSpec } from "../api/types";
import { TickerSearch } from "../components/TickerSearch";

interface Props {
  onCreated: (p: Portfolio) => void;
  onCancel: () => void;
  // When provided, seed the holdings (e.g. from the Optimize "Save as portfolio").
  initialWeights?: Record<string, number>;
  initialName?: string;
  initialBenchmark?: string;
  // When provided, open in "Actual purchases" mode seeded with these lots so an
  // existing lot-based portfolio round-trips for editing.
  initialLots?: Lot[];
}

// "weight" and "amount" build a weighted portfolio; "purchases" builds a
// lot-based (actual-purchases) spec where each row is a dated buy.
type EntryMode = "weight" | "amount" | "purchases";

interface WeightRow {
  symbol: string;
  amount: number; // interpreted per the active mode (weight fraction or $)
}

// A dated-purchase row. `key` is a stable client id (a symbol can appear on
// multiple dates, so we can't key by symbol).
interface LotRow {
  key: number;
  symbol: string;
  date: string; // YYYY-MM-DD
  amount: number; // dollars invested
}

function today(): string {
  // Local calendar date (toISOString is UTC — off by one around midnight).
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function NewPortfolio({
  onCreated,
  onCancel,
  initialWeights,
  initialName,
  initialBenchmark,
  initialLots,
}: Props) {
  const create = useCreatePortfolio();
  const [name, setName] = useState(initialName ?? "");
  const [benchmark, setBenchmark] = useState(initialBenchmark ?? "SPY");
  const [mode, setMode] = useState<EntryMode>(
    initialLots && initialLots.length > 0 ? "purchases" : "weight",
  );
  const [rows, setRows] = useState<WeightRow[]>(
    initialWeights
      ? Object.entries(initialWeights).map(([symbol, w]) => ({ symbol, amount: w }))
      : [],
  );

  // Lot rows (Actual purchases mode). Seeded from initialLots for round-trip
  // edit; keys are index-based initially and the counter continues from there.
  const [lotRows, setLotRows] = useState<LotRow[]>(() =>
    (initialLots ?? []).map((l, i) => ({ key: i, ...l })),
  );
  const lotKey = useRef(initialLots?.length ?? 0);

  // Contribution plan (weighted modes only).
  const [lumpSum, setLumpSum] = useState(1000);
  const [recurring, setRecurring] = useState(0);
  const [frequency, setFrequency] = useState("monthly");

  const [error, setError] = useState<string | null>(null);

  // --- Weighted-row helpers ---
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

  // --- Lot-row helpers (a symbol may repeat, so add always appends a row) ---
  function addLot(symbol: string) {
    setLotRows((prev) => [
      ...prev,
      { key: lotKey.current++, symbol, date: today(), amount: 0 },
    ]);
  }
  function removeLot(key: number) {
    setLotRows((prev) => prev.filter((r) => r.key !== key));
  }
  function setLotField<K extends "date" | "amount">(
    key: number,
    field: K,
    value: LotRow[K],
  ) {
    setLotRows((prev) =>
      prev.map((r) => (r.key === key ? { ...r, [field]: value } : r)),
    );
  }

  // Derive normalized weights (sum to 1) from rows under the active mode.
  function computeWeights(): Record<string, number> | null {
    if (rows.length === 0 || total <= 0) return null;
    const w: Record<string, number> = {};
    for (const r of rows) w[r.symbol] = (r.amount || 0) / total;
    return w;
  }

  function buildSpec(): PortfolioSpec | string {
    const trimmed = name.trim();
    if (!trimmed) return "Give the portfolio a name.";
    const bench = benchmark.trim().toUpperCase();
    if (!bench) return "Pick a benchmark.";

    if (mode === "purchases") {
      if (lotRows.length === 0) return "Add at least one purchase.";
      const max = today();
      const lots: Lot[] = [];
      for (const r of lotRows) {
        if (!(r.amount > 0)) return `Enter a positive amount for ${r.symbol}.`;
        if (!r.date) return `Pick a purchase date for ${r.symbol}.`;
        if (Number.isNaN(Date.parse(r.date)))
          return `Invalid date for ${r.symbol}.`;
        if (r.date > max) return `${r.symbol}: purchase date can't be in the future.`;
        lots.push({ symbol: r.symbol, date: r.date, amount: r.amount });
      }
      // Lot-based spec: holdings + contributions are empty by contract.
      return {
        name: trimmed,
        benchmark_symbol: bench,
        base_currency: "USD",
        holdings: [],
        contributions: [],
        lots,
      };
    }

    const weights = computeWeights();
    if (!weights) return "Add at least one holding with a positive value.";

    // In $-amount mode the lump sum IS the sum of the per-ticker dollars (weights
    // still derive from the same amounts); the separate lump-sum field is ignored.
    const lump = mode === "amount" ? total : lumpSum;
    const contributions: Contribution[] = [];
    if (lump > 0) contributions.push({ kind: "lump_sum", amount: lump });
    if (recurring > 0)
      contributions.push({ kind: "recurring", amount: recurring, frequency });

    return {
      name: trimmed,
      benchmark_symbol: bench,
      base_currency: "USD",
      holdings: Object.entries(weights).map(([symbol, weight]) => ({ symbol, weight })),
      contributions,
    };
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const spec = buildSpec();
    if (typeof spec === "string") return setError(spec);

    try {
      const created = await create.mutateAsync(spec);
      onCreated(created);
    } catch (err) {
      const msg = apiErrorMessage(err, "Could not save the portfolio.");
      setError(msg);
      toast.error(msg);
    }
  }

  const purchases = mode === "purchases";
  const maxDate = today();

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
            onChange={(e) => setMode(e.target.value as EntryMode)}
            className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
          >
            <option value="weight">Weights (relative)</option>
            <option value="amount">Dollar amounts</option>
            <option value="purchases">Actual purchases (dates)</option>
          </select>
        </label>
      </div>

      {purchases ? (
        <>
          <p className="text-xs text-content-muted dark:text-content-dark-muted">
            Enter each buy you actually made — the ticker, the date, and the dollars
            invested. Entry timing (per-stock buy dates) drives performance; the chart
            starts at your earliest purchase.
          </p>

          <div>
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Add a purchase
            </span>
            <TickerSearch onSelect={addLot} placeholder="Search ticker to add a buy…" />
          </div>

          {lotRows.length > 0 && (
            <div className="rounded-md border border-edge dark:border-edge-dark">
              <div className="flex items-center gap-3 border-b border-edge/60 px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-content-muted dark:border-edge-dark/60 dark:text-content-dark-muted">
                <span className="w-16">Ticker</span>
                <span className="w-40">Date bought</span>
                <span className="w-28">Amount ($)</span>
              </div>
              {lotRows.map((r) => (
                <div
                  key={r.key}
                  className="flex flex-wrap items-center gap-3 border-b border-edge/60 px-3 py-2 last:border-b-0 dark:border-edge-dark/60"
                >
                  <span className="w-16 text-sm font-medium">{r.symbol}</span>
                  <input
                    type="date"
                    max={maxDate}
                    value={r.date}
                    aria-label={`${r.symbol} purchase date`}
                    onChange={(e) => setLotField(r.key, "date", e.target.value)}
                    className="w-40 min-w-0 rounded-md border border-edge bg-surface px-2 py-1 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
                  />
                  <input
                    type="number"
                    min={0}
                    step={100}
                    value={r.amount}
                    aria-label={`${r.symbol} amount invested in dollars`}
                    onChange={(e) =>
                      setLotField(r.key, "amount", Number(e.target.value))
                    }
                    className="w-28 min-w-0 rounded-md border border-edge bg-surface px-2 py-1 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
                  />
                  <button
                    type="button"
                    onClick={() => removeLot(r.key)}
                    className="ml-auto text-content-muted hover:text-down dark:text-content-dark-muted"
                    aria-label={`Remove ${r.symbol} purchase`}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <>
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
        </>
      )}

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
