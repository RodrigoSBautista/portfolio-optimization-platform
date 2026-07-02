import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { toast } from "sonner";
import { apiErrorMessage } from "../api/client";
import { useSimulation } from "../api/queries";
import type { Portfolio, SimulateRequest } from "../api/types";
import { GrowthChart } from "../charts/GrowthChart";
import { Card, SectionHeader } from "../components/Card";
import { KpiCard } from "../components/KpiCard";
import { MetricsTable } from "../components/MetricsTable";
import { ChartSkeleton, KpiGridSkeleton, TableSkeleton } from "../components/Skeleton";
import { crossFade, staggerContainer } from "../lib/motion";
import { RANGES, startForRange, type RangeKey } from "../lib/dates";
import { formatCurrency, formatSignedCurrency, metricSign } from "../lib/format";

interface Props {
  portfolio: Portfolio;
  onDelete?: () => void;
}

export function Dashboard({ portfolio, onDelete }: Props) {
  const [range, setRange] = useState<RangeKey>("1Y");
  const reduce = useReducedMotion();

  const req = useMemo<SimulateRequest>(
    () => ({
      spec: portfolio,
      start: startForRange(range),
      benchmark: portfolio.benchmark_symbol,
    }),
    [portfolio, range],
  );

  const { data, isLoading, isError, error } = useSimulation(req);

  // Surface API failures as a toast (in addition to the inline banner).
  useEffect(() => {
    if (isError) {
      toast.error(apiErrorMessage(error, "Could not run the simulation for this range."));
    }
  }, [isError, error]);

  const gain = data ? data.final_value - data.invested : 0;

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
        <div className="flex items-center gap-2">
          <div className="flex gap-1 rounded-lg border border-edge bg-surface-alt p-1 dark:border-edge-dark dark:bg-surface-dark-alt">
            {RANGES.map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`rounded-md px-3 py-1 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                  range === r
                    ? "bg-surface text-content shadow-sm dark:bg-surface-dark dark:text-content-dark"
                    : "text-content-muted hover:text-content dark:text-content-dark-muted dark:hover:text-content-dark"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          {onDelete && (
            <button
              onClick={() => {
                if (
                  window.confirm(`Delete "${portfolio.name}"? This cannot be undone.`)
                ) {
                  onDelete();
                }
              }}
              className="rounded-lg border border-edge px-3 py-1.5 text-sm font-medium text-content-muted transition hover:border-down/40 hover:bg-down/10 hover:text-down focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-down dark:border-edge-dark dark:text-content-dark-muted"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {isError && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
          {apiErrorMessage(error, "Could not run the simulation for this range.")}
        </div>
      )}

      {isLoading && (
        <>
          <Card className="p-3">
            <ChartSkeleton />
          </Card>
          <KpiGridSkeleton />
        </>
      )}

      {data && !isLoading && (
        <>
          <Card className="p-3">
            {/* Cross-fade the chart when the range (data) changes. */}
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={range}
                variants={reduce ? undefined : crossFade}
                initial={reduce ? false : "hidden"}
                animate={reduce ? undefined : "show"}
                exit={reduce ? undefined : "exit"}
              >
                <GrowthChart
                  series={data.series}
                  // Trend color follows the time-weighted return so the chart agrees
                  // with the "Total return" KPI and the metrics table.
                  trendSign={metricSign(data.metrics[portfolio.name]?.["Total return"])}
                  benchmarkLabel={data.benchmark}
                />
              </motion.div>
            </AnimatePresence>
          </Card>

          {data.dropped.length > 0 && (
            <div className="text-xs text-content-muted dark:text-content-dark-muted">
              Dropped (no data in window): {data.dropped.join(", ")}
            </div>
          )}

          {/*
            Dollar tiles are cost-basis (money in vs money out) and animate via
            count-up. The percentage tile uses the TIME-WEIGHTED "Total return"
            string from metrics (rendered verbatim, never count-up) so the KPI %,
            the metrics table, and the chart trend all agree.
          */}
          <motion.div
            className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
            variants={reduce ? undefined : staggerContainer}
            initial={reduce ? false : "hidden"}
            animate={reduce ? undefined : "show"}
          >
            <KpiCard
              label="Final value"
              value={formatCurrency(data.final_value)}
              countTo={data.final_value}
              format={formatCurrency}
            />
            <KpiCard
              label="Total invested (cost basis)"
              value={formatCurrency(data.invested)}
              countTo={data.invested}
              format={formatCurrency}
            />
            <KpiCard
              label="Net gain ($, value − invested)"
              value={formatSignedCurrency(gain)}
              countTo={gain}
              format={formatSignedCurrency}
              tone={gain >= 0 ? "up" : "down"}
            />
            <KpiCard
              label="Total return (%, time-weighted)"
              value={data.metrics[portfolio.name]?.["Total return"] ?? "—"}
              tone={
                metricSign(data.metrics[portfolio.name]?.["Total return"]) >= 0
                  ? "up"
                  : "down"
              }
            />
            {renderMetricKpis(data.metrics, portfolio.name)}
          </motion.div>

          <Card className="p-4">
            <SectionHeader>Metrics</SectionHeader>
            <MetricsTable metrics={data.metrics} />
          </Card>
        </>
      )}

      {isLoading && (
        <Card className="p-4">
          <SectionHeader>Metrics</SectionHeader>
          <TableSkeleton />
        </Card>
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
