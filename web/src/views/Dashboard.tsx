import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { toast } from "sonner";
import { apiErrorMessage } from "../api/client";
import { useSimulation } from "../api/queries";
import type { Portfolio, RebalanceCadence, SimulateRequest } from "../api/types";
import { GrowthChart } from "../charts/GrowthChart";
import { Card, SectionHeader } from "../components/Card";
import { KpiCard } from "../components/KpiCard";
import { MetricsTable } from "../components/MetricsTable";
import { ChartSkeleton, KpiGridSkeleton, TableSkeleton } from "../components/Skeleton";
import { crossFade, staggerContainer } from "../lib/motion";
import { CRISIS_PRESETS, RANGES, startForRange, type RangeKey } from "../lib/dates";
import { formatCurrency, formatSignedCurrency, metricSign } from "../lib/format";
import { AdvancedOptions } from "./dashboard/AdvancedOptions";
import {
  DEFAULT_ADVANCED,
  type AdvancedSimOptions,
} from "./dashboard/advanced-options";
import { AnalyticsSection } from "./dashboard/AnalyticsSection";

interface Props {
  portfolio: Portfolio;
  onDelete?: () => void;
}

export function Dashboard({ portfolio, onDelete }: Props) {
  const [range, setRange] = useState<RangeKey>("1Y");
  // A selected crisis preset overrides the range with an explicit start+end.
  const [presetKey, setPresetKey] = useState<string | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [adv, setAdv] = useState<AdvancedSimOptions>(DEFAULT_ADVANCED);
  const reduce = useReducedMotion();

  const preset = CRISIS_PRESETS.find((p) => p.key === presetKey) ?? null;

  const rebalance: RebalanceCadence | null =
    adv.rebalance === "none" ? null : adv.rebalance;

  const req = useMemo<SimulateRequest>(
    () => ({
      spec: portfolio,
      start: preset ? preset.start : startForRange(range),
      end: preset ? preset.end : null,
      benchmark: portfolio.benchmark_symbol,
      rebalance,
      risk_free_rate: adv.riskFreePct / 100,
      inflation_pct: adv.inflationOn ? adv.inflationPct : null,
      escalation_pct: adv.escalationPct,
      annual_fee_pct: adv.annualFeePct,
      include_analytics: showAnalytics,
    }),
    [portfolio, range, preset, rebalance, adv, showAnalytics],
  );

  const { data, isLoading, isError, error } = useSimulation(req);

  // Surface API failures as a toast (in addition to the inline banner).
  useEffect(() => {
    if (isError) {
      toast.error(apiErrorMessage(error, "Could not run the simulation for this range."));
    }
  }, [isError, error]);

  const gain = data ? data.final_value - data.invested : 0;
  const inflationView = adv.inflationOn && data?.real_final_value != null;

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
                onClick={() => {
                  // Any range-tab click clears an active crisis preset.
                  setPresetKey(null);
                  setRange(r);
                }}
                className={`rounded-md px-3 py-1 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                  !preset && range === r
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

      {/* Crisis preset chips — set an explicit start+end drawdown window. */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-content-muted dark:text-content-dark-muted">
          Crisis windows:
        </span>
        {CRISIS_PRESETS.map((p) => {
          const active = presetKey === p.key;
          return (
            <button
              key={p.key}
              onClick={() => setPresetKey(active ? null : p.key)}
              aria-pressed={active}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                active
                  ? "border-brand bg-brand/10 text-brand"
                  : "border-edge text-content-muted hover:text-content dark:border-edge-dark dark:text-content-dark-muted dark:hover:text-content-dark"
              }`}
            >
              {p.label}
            </button>
          );
        })}
        {preset && (
          <span className="text-xs text-content-muted dark:text-content-dark-muted">
            {preset.start} → {preset.end}
          </span>
        )}
      </div>

      <AdvancedOptions value={adv} onChange={setAdv} />

      <label className="flex items-center gap-2 text-sm text-content-muted dark:text-content-dark-muted">
        <input
          type="checkbox"
          checked={showAnalytics}
          onChange={(e) => setShowAnalytics(e.target.checked)}
          className="h-4 w-4 accent-brand"
        />
        Show analytics (drawdown &amp; rolling return/volatility)
      </label>

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
          {inflationView && (
            <div className="rounded-lg border border-edge bg-surface-alt px-3 py-2 text-xs text-content-muted dark:border-edge-dark dark:bg-surface-dark-alt dark:text-content-dark-muted">
              Chart and final value shown in <strong>today&apos;s dollars</strong>{" "}
              (adjusted for {adv.inflationPct}%/yr inflation).
            </div>
          )}
          <Card className="p-3">
            {/* Cross-fade the chart when the range (data) changes. */}
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={`${presetKey ?? range}-${inflationView ? "real" : "nominal"}`}
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
                  valueKey={inflationView ? "real_value" : "value"}
                  valueLabel={inflationView ? "Value (today's $)" : "Value"}
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
              label={inflationView ? "Final value (today's $)" : "Final value"}
              value={formatCurrency(
                inflationView ? (data.real_final_value as number) : data.final_value,
              )}
              countTo={
                inflationView ? (data.real_final_value as number) : data.final_value
              }
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
                data.metrics[portfolio.name]?.["Total return"] == null
                  ? "neutral" // missing metric renders the "—" placeholder uncolored
                  : metricSign(data.metrics[portfolio.name]?.["Total return"]) >= 0
                    ? "up"
                    : "down"
              }
            />
            {renderMetricKpis(data.metrics, portfolio.name)}
          </motion.div>

          {showAnalytics && (
            <AnalyticsSection
              loading={false}
              drawdown={data.drawdown}
              rolling={data.rolling}
            />
          )}

          <Card className="p-4">
            <SectionHeader>Metrics</SectionHeader>
            <MetricsTable metrics={data.metrics} />
          </Card>
        </>
      )}

      {isLoading && showAnalytics && <AnalyticsSection loading />}

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
