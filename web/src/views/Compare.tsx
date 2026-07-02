import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { toast } from "sonner";
import { apiErrorMessage } from "../api/client";
import { useCompare } from "../api/queries";
import type { CompareRequest, Metrics } from "../api/types";
import { MultiSeriesChart, type NamedSeries } from "../charts/MultiSeriesChart";
import { Card, SectionHeader } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { CompareIcon } from "../components/icons";
import { MetricsTable } from "../components/MetricsTable";
import { ChartSkeleton, KpiGridSkeleton } from "../components/Skeleton";
import { BENCHMARK_INDICES } from "../lib/benchmarks";
import { startForRange, type RangeKey } from "../lib/dates";
import { formatCurrency, formatSignedCurrency, seriesColorClass } from "../lib/format";
import { staggerContainer, riseItem } from "../lib/motion";
import { seriesColor } from "../theme/colors";
import { useShell } from "./shell-context";

const RANGES: RangeKey[] = ["1Y", "5Y", "MAX"];

export function Compare() {
  const { portfolios, openNew } = useShell();
  const reduce = useReducedMotion();
  const [ids, setIds] = useState<number[]>([]);
  const [range, setRange] = useState<RangeKey>("5Y");
  const [benchmark, setBenchmark] = useState("SPY");
  const [req, setReq] = useState<CompareRequest | null>(null);

  const { data, isFetching, isError, error } = useCompare(req);

  useEffect(() => {
    if (isError) toast.error(apiErrorMessage(error, "Could not compare these portfolios."));
  }, [isError, error]);

  function toggle(id: number) {
    setIds((cur) => {
      if (cur.includes(id)) return cur.filter((x) => x !== id);
      if (cur.length >= 3) return cur; // cap at 3
      return [...cur, id];
    });
  }

  const valid = ids.length >= 2 && ids.length <= 3;

  function run() {
    if (!valid) return;
    setReq({
      portfolio_ids: ids,
      start: startForRange(range),
      benchmark: benchmark.toUpperCase(),
    });
  }

  if (portfolios.length < 2) {
    return (
      <div className="p-4 md:p-6">
        <Header />
        <div className="mt-4">
          <EmptyState
            icon={<CompareIcon size={40} />}
            title="Need at least two portfolios"
            message="Compare puts 2–3 of your saved portfolios on one chart. Create another portfolio to get started."
            actionLabel="+ New portfolio"
            onAction={openNew}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <Header />

      {/* Controls */}
      <Card className="flex flex-col gap-4 p-4">
        <div>
          <div className="mb-2 text-xs font-medium text-content-muted dark:text-content-dark-muted">
            Pick 2–3 portfolios
          </div>
          <div className="flex flex-wrap gap-2">
            {portfolios.map((p) => {
              const idx = ids.indexOf(p.id);
              const on = idx >= 0;
              return (
                <button
                  key={p.id}
                  onClick={() => toggle(p.id)}
                  aria-pressed={on}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                    on
                      ? "border-brand bg-brand/10 text-brand"
                      : "border-edge text-content-muted hover:text-content dark:border-edge-dark dark:text-content-dark-muted dark:hover:text-content-dark"
                  }`}
                >
                  {on && (
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{ background: seriesColor(idx) }}
                    />
                  )}
                  {p.name}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Since
            </span>
            <select
              value={range}
              onChange={(e) => setRange(e.target.value as RangeKey)}
              className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
            >
              {RANGES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Benchmark
            </span>
            <select
              value={benchmark}
              onChange={(e) => setBenchmark(e.target.value)}
              className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
            >
              {BENCHMARK_INDICES.map((b) => (
                <option key={b.symbol} value={b.symbol}>
                  {b.name}
                </option>
              ))}
            </select>
          </label>
          <button
            onClick={run}
            disabled={!valid}
            className="ml-auto rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-50"
          >
            Compare
          </button>
        </div>
        {!valid && (
          <p className="text-xs text-content-muted dark:text-content-dark-muted">
            Select 2 or 3 portfolios to enable the comparison.
          </p>
        )}
      </Card>

      {isFetching && (
        <>
          <Card className="p-3">
            <ChartSkeleton />
          </Card>
          <KpiGridSkeleton count={ids.length || 3} />
        </>
      )}

      {isError && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
          {apiErrorMessage(error, "Could not compare these portfolios.")}
        </div>
      )}

      {data && !isFetching && <Results data={data} reduce={!!reduce} />}
    </div>
  );
}

function Header() {
  return (
    <div>
      <h1 className="text-xl font-semibold">Compare</h1>
      <p className="text-sm text-content-muted dark:text-content-dark-muted">
        Put 2–3 of your portfolios on one chart, from a shared start date against
        a common benchmark.
      </p>
    </div>
  );
}

function Results({
  data,
  reduce,
}: {
  data: NonNullable<ReturnType<typeof useCompare>["data"]>;
  reduce: boolean;
}) {
  const series: NamedSeries[] = data.results.map((r) => ({
    key: `p${r.id}`,
    label: r.name,
    points: r.series,
  }));

  const benchmark = data.benchmark_series
    ? { label: "Benchmark", points: data.benchmark_series }
    : null;

  // Build a metrics table with one column per portfolio + a benchmark column.
  const metrics: Metrics = useMemo(() => {
    const m: Metrics = {};
    for (const r of data.results) m[r.name] = r.metrics;
    if (data.benchmark_metrics) m["Benchmark"] = data.benchmark_metrics;
    return m;
  }, [data]);

  return (
    <>
      <Card className="p-3">
        <MultiSeriesChart series={series} benchmark={benchmark} />
      </Card>

      {/* Side-by-side KPI columns. Invested is EQUAL across portfolios by design. */}
      <motion.div
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        variants={reduce ? undefined : staggerContainer}
        initial={reduce ? false : "hidden"}
        animate={reduce ? undefined : "show"}
      >
        {data.results.map((r, i) => {
          const gain = r.final_value - r.invested;
          return (
            <motion.div
              key={r.id}
              variants={reduce ? undefined : riseItem}
              className="rounded-xl border border-edge bg-surface-alt p-4 shadow-card dark:border-edge-dark dark:bg-surface-dark-alt dark:shadow-none"
            >
              <div className="mb-2 flex items-center gap-2">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ background: seriesColor(i) }}
                />
                <span className="truncate text-sm font-semibold">{r.name}</span>
              </div>
              <dl className="flex flex-col gap-1.5 text-sm">
                <Row label="Final value" value={formatCurrency(r.final_value)} />
                <Row label="Invested" value={formatCurrency(r.invested)} />
                <Row
                  label="Gain"
                  value={formatSignedCurrency(gain)}
                  className={seriesColorClass(gain)}
                />
              </dl>
            </motion.div>
          );
        })}
      </motion.div>
      <p className="text-xs text-content-muted dark:text-content-dark-muted">
        Invested (cost basis) is equal across portfolios by design — the same
        contribution plan is applied to each so only the allocations differ.
      </p>

      <Card className="p-4">
        <SectionHeader>Metrics</SectionHeader>
        <MetricsTable metrics={metrics} />
      </Card>
    </>
  );
}

function Row({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-content-muted dark:text-content-dark-muted">{label}</dt>
      <dd className={`font-semibold tabular-nums ${className}`}>{value}</dd>
    </div>
  );
}
