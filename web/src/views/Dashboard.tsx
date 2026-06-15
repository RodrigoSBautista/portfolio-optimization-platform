import { useMemo, useState } from "react";
import { apiErrorMessage } from "../api/client";
import { useSimulation } from "../api/queries";
import type { Portfolio, SimulateRequest } from "../api/types";
import { GrowthChart } from "../charts/GrowthChart";
import { KpiCard } from "../components/KpiCard";
import { MetricsTable } from "../components/MetricsTable";
import { RANGES, startForRange, type RangeKey } from "../lib/dates";
import { formatCurrency, formatPct, formatSignedCurrency } from "../lib/format";

interface Props {
  portfolio: Portfolio;
}

export function Dashboard({ portfolio }: Props) {
  const [range, setRange] = useState<RangeKey>("1Y");

  const req = useMemo<SimulateRequest>(
    () => ({
      spec: portfolio,
      start: startForRange(range),
      benchmark: portfolio.benchmark_symbol,
    }),
    [portfolio, range],
  );

  const { data, isLoading, isError, error } = useSimulation(req);

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{portfolio.name}</h1>
          <p className="text-sm text-content-muted dark:text-content-dark-muted">
            {portfolio.holdings.map((h) => h.symbol).join(", ")} · benchmark{" "}
            {portfolio.benchmark_symbol}
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border border-edge bg-surface-alt p-1 dark:border-edge-dark dark:bg-surface-dark-alt">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                range === r
                  ? "bg-surface text-content shadow-sm dark:bg-surface-dark dark:text-content-dark"
                  : "text-content-muted hover:text-content dark:text-content-dark-muted dark:hover:text-content-dark"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {isError && (
        <div className="rounded-md border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
          {apiErrorMessage(error, "Could not run the simulation for this range.")}
        </div>
      )}

      {isLoading && (
        <div className="flex h-80 items-center justify-center text-content-muted dark:text-content-dark-muted">
          Running simulation…
        </div>
      )}

      {data && !isLoading && (
        <>
          <div className="rounded-lg border border-edge bg-surface p-3 dark:border-edge-dark dark:bg-surface-dark">
            <GrowthChart
              series={data.series}
              gainPct={data.gain_pct}
              benchmarkLabel={data.benchmark}
            />
          </div>

          {data.dropped.length > 0 && (
            <div className="text-xs text-content-muted dark:text-content-dark-muted">
              Dropped (no data in window): {data.dropped.join(", ")}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <KpiCard label="Final value" value={formatCurrency(data.final_value)} />
            <KpiCard label="Total invested" value={formatCurrency(data.invested)} />
            <KpiCard
              label="Gain ($)"
              value={formatSignedCurrency(data.final_value - data.invested)}
              tone={data.final_value - data.invested >= 0 ? "up" : "down"}
            />
            <KpiCard
              label="Gain (%)"
              value={formatPct(data.gain_pct)}
              tone={data.gain_pct >= 0 ? "up" : "down"}
            />
            {renderMetricKpis(data.metrics, portfolio.name)}
          </div>

          <section className="rounded-lg border border-edge bg-surface p-4 dark:border-edge-dark dark:bg-surface-dark">
            <h2 className="mb-3 text-sm font-semibold">Metrics</h2>
            <MetricsTable metrics={data.metrics} />
          </section>
        </>
      )}
    </div>
  );
}

// Pull a few headline metrics from the portfolio's own metric block into KPI tiles.
function renderMetricKpis(
  metrics: Record<string, Record<string, string>>,
  name: string,
) {
  const block = metrics[name];
  if (!block) return null;
  const wanted = ["CAGR", "Volatility (ann.)", "Sharpe", "Max drawdown"];
  return wanted
    .filter((m) => block[m] != null)
    .map((m) => <KpiCard key={m} label={m} value={block[m]} />);
}
