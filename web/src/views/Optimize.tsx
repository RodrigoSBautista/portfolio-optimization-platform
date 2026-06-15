import { useState } from "react";
import { apiErrorMessage } from "../api/client";
import { useOptimize } from "../api/queries";
import {
  ALLOCATION_METHODS,
  SELECTION_METHODS,
  type AllocationMethod,
  type OptimizeMode,
  type OptimizeRequest,
  type SelectionMethod,
} from "../api/types";
import { ComparisonChart } from "../charts/ComparisonChart";
import { WeightsBar } from "../charts/WeightsBar";
import { MetricsTable } from "../components/MetricsTable";
import { TickerSearch } from "../components/TickerSearch";

interface Props {
  onSaveAsPortfolio: (weights: Record<string, number>, benchmark: string) => void;
}

export function Optimize({ onSaveAsPortfolio }: Props) {
  const optimize = useOptimize();
  const [mode, setMode] = useState<OptimizeMode>("allocate");
  const [method, setMethod] = useState<AllocationMethod>("Risk parity");
  const [selectionMethod, setSelectionMethod] =
    useState<SelectionMethod>("Low volatility");
  const [tickers, setTickers] = useState<string[]>([]);
  const [benchmark, setBenchmark] = useState("SPY");
  const [lookback, setLookback] = useState(5);
  const [maxWeight, setMaxWeight] = useState(40); // percent
  const [k, setK] = useState(5);
  const [error, setError] = useState<string | null>(null);

  function addTicker(symbol: string) {
    if (!tickers.includes(symbol)) setTickers([...tickers, symbol]);
  }
  function removeTicker(symbol: string) {
    setTickers(tickers.filter((t) => t !== symbol));
  }

  async function run() {
    setError(null);
    if (tickers.length < 2) {
      setError("Add at least two tickers.");
      return;
    }
    const req: OptimizeRequest = {
      mode,
      method,
      benchmark: benchmark.toUpperCase(),
      lookback_years: lookback,
      max_weight: maxWeight / 100,
      ...(mode === "allocate"
        ? { tickers }
        : { candidates: tickers, k, selection_method: selectionMethod }),
    };
    try {
      await optimize.mutateAsync(req);
    } catch (err) {
      setError(apiErrorMessage(err, "Optimization failed."));
    }
  }

  const result = optimize.data;

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <div>
        <h1 className="text-xl font-semibold">Optimize</h1>
        <p className="text-sm text-content-muted dark:text-content-dark-muted">
          Suggest weights and compare against an equal-weight baseline and a benchmark.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        {/* Controls */}
        <div className="flex flex-col gap-3 rounded-lg border border-edge bg-surface p-4 dark:border-edge-dark dark:bg-surface-dark">
          <div className="flex gap-1 rounded-md border border-edge p-1 dark:border-edge-dark">
            {(["allocate", "select"] as OptimizeMode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 rounded px-3 py-1.5 text-sm font-medium capitalize ${
                  mode === m
                    ? "bg-brand text-white"
                    : "text-content-muted hover:text-content dark:text-content-dark-muted"
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Allocation method
            </span>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value as AllocationMethod)}
              className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
            >
              {ALLOCATION_METHODS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>

          {mode === "select" && (
            <>
              <label className="block">
                <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                  Selection method
                </span>
                <select
                  value={selectionMethod}
                  onChange={(e) =>
                    setSelectionMethod(e.target.value as SelectionMethod)
                  }
                  className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
                >
                  {SELECTION_METHODS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                  Keep top k: {k}
                </span>
                <input
                  type="range"
                  min={1}
                  max={Math.max(1, tickers.length)}
                  value={k}
                  onChange={(e) => setK(Number(e.target.value))}
                  className="w-full accent-brand"
                />
              </label>
            </>
          )}

          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Lookback: {lookback} yr
            </span>
            <input
              type="range"
              min={1}
              max={10}
              value={lookback}
              onChange={(e) => setLookback(Number(e.target.value))}
              className="w-full accent-brand"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Max weight: {maxWeight}%
            </span>
            <input
              type="range"
              min={5}
              max={100}
              step={5}
              value={maxWeight}
              onChange={(e) => setMaxWeight(Number(e.target.value))}
              className="w-full accent-brand"
            />
          </label>

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

          <div>
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              {mode === "allocate" ? "Tickers" : "Candidates"}
            </span>
            <TickerSearch onSelect={addTicker} exclude={tickers} />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {tickers.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 rounded-full bg-surface-alt px-2 py-0.5 text-xs dark:bg-surface-dark-alt"
                >
                  {t}
                  <button
                    onClick={() => removeTicker(t)}
                    className="text-content-muted hover:text-down dark:text-content-dark-muted"
                    aria-label={`Remove ${t}`}
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          </div>

          {error && (
            <div className="rounded-md border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
              {error}
            </div>
          )}

          <button
            onClick={run}
            disabled={optimize.isPending}
            className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
          >
            {optimize.isPending ? "Optimizing…" : "Run optimization"}
          </button>
        </div>

        {/* Results */}
        <div className="flex flex-col gap-4">
          {!result && !optimize.isPending && (
            <div className="flex h-full min-h-[300px] items-center justify-center rounded-lg border border-dashed border-edge text-sm text-content-muted dark:border-edge-dark dark:text-content-dark-muted">
              Pick tickers and run an optimization to see suggested weights.
            </div>
          )}

          {result && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-content-muted dark:text-content-dark-muted">
                  Selected: {result.selected.join(", ")}
                </p>
                <button
                  onClick={() =>
                    onSaveAsPortfolio(result.suggested, benchmark.toUpperCase())
                  }
                  className="rounded-md border border-edge px-3 py-1.5 text-sm font-medium hover:bg-surface-alt dark:border-edge-dark dark:hover:bg-surface-dark-alt"
                >
                  Save as portfolio
                </button>
              </div>

              <section className="rounded-lg border border-edge bg-surface p-4 dark:border-edge-dark dark:bg-surface-dark">
                <h2 className="mb-3 text-sm font-semibold">
                  Suggested vs equal weight
                </h2>
                <WeightsBar suggested={result.suggested} baseline={result.baseline} />
              </section>

              <section className="rounded-lg border border-edge bg-surface p-4 dark:border-edge-dark dark:bg-surface-dark">
                <h2 className="mb-3 text-sm font-semibold">Growth comparison</h2>
                <ComparisonChart
                  series={result.comparison_series}
                  benchmarkLabel={benchmark.toUpperCase()}
                />
              </section>

              <section className="rounded-lg border border-edge bg-surface p-4 dark:border-edge-dark dark:bg-surface-dark">
                <h2 className="mb-3 text-sm font-semibold">Metrics</h2>
                <MetricsTable metrics={result.metrics} />
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
