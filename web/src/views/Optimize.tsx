import { useState } from "react";
import { toast } from "sonner";
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
import { Card, SectionHeader } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { SparklesIcon } from "../components/icons";
import { MetricsTable } from "../components/MetricsTable";
import { ChartSkeleton, TableSkeleton } from "../components/Skeleton";
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

  // How many holdings the suggestion will actually allocate across: all tickers in
  // allocate mode, else the top-k (capped at the candidate count) in select mode.
  const allocatedCount =
    mode === "select" ? Math.min(k, tickers.length) : tickers.length;
  // A cap below 100/count is infeasible (weights can't sum to 1), so clamp the
  // slider's floor to ceil(100 / count).
  const minMaxWeight = allocatedCount > 0 ? Math.ceil(100 / allocatedCount) : 5;
  const effectiveMaxWeight = Math.max(maxWeight, minMaxWeight);

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
      max_weight: effectiveMaxWeight / 100,
      ...(mode === "allocate"
        ? { tickers }
        : { candidates: tickers, k, selection_method: selectionMethod }),
    };
    try {
      await optimize.mutateAsync(req);
    } catch (err) {
      const msg = apiErrorMessage(err, "Optimization failed.");
      setError(msg);
      toast.error(msg);
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
              Max weight: {effectiveMaxWeight}%
            </span>
            <input
              type="range"
              min={minMaxWeight}
              max={100}
              step={5}
              value={effectiveMaxWeight}
              onChange={(e) => setMaxWeight(Number(e.target.value))}
              className="w-full accent-brand"
            />
            {maxWeight < minMaxWeight && allocatedCount > 0 && (
              <span className="mt-1 block text-xs text-content-muted dark:text-content-dark-muted">
                Raised to {minMaxWeight}% — a lower cap can't fill{" "}
                {allocatedCount} holdings.
              </span>
            )}
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
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:opacity-60 dark:focus-visible:ring-offset-surface-dark"
          >
            {optimize.isPending ? "Optimizing…" : "Run optimization"}
          </button>
        </div>

        {/* Results */}
        <div className="flex flex-col gap-4">
          {!result && !optimize.isPending && (
            <EmptyState
              icon={<SparklesIcon size={40} />}
              title="No optimization yet"
              message="Pick tickers and run an optimization to see suggested weights vs an equal-weight baseline and a benchmark."
            />
          )}

          {optimize.isPending && (
            <>
              <Card className="p-4">
                <SectionHeader>Suggested vs equal weight</SectionHeader>
                <ChartSkeleton height={220} />
              </Card>
              <Card className="p-4">
                <SectionHeader>Growth comparison</SectionHeader>
                <ChartSkeleton height={280} />
              </Card>
              <Card className="p-4">
                <SectionHeader>Metrics</SectionHeader>
                <TableSkeleton />
              </Card>
            </>
          )}

          {result && !optimize.isPending && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-content-muted dark:text-content-dark-muted">
                  Selected: {result.selected.join(", ")}
                </p>
                <button
                  onClick={() =>
                    onSaveAsPortfolio(result.suggested, benchmark.toUpperCase())
                  }
                  className="rounded-lg border border-edge px-3 py-1.5 text-sm font-medium transition hover:bg-surface-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand dark:border-edge-dark dark:hover:bg-surface-dark-alt"
                >
                  Save as portfolio
                </button>
              </div>

              <Card className="p-4">
                <SectionHeader>Suggested vs equal weight</SectionHeader>
                <WeightsBar suggested={result.suggested} baseline={result.baseline} />
              </Card>

              <Card className="p-4">
                <SectionHeader>Growth comparison</SectionHeader>
                <ComparisonChart
                  series={result.comparison_series}
                  benchmarkLabel={benchmark.toUpperCase()}
                />
              </Card>

              <Card className="p-4">
                <SectionHeader>Metrics</SectionHeader>
                <MetricsTable metrics={result.metrics} />
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
