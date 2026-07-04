import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiErrorMessage } from "../api/client";
import { useProjection, useSimulation } from "../api/queries";
import type { ProjectRequest, SimulateRequest } from "../api/types";
import { FanChart } from "../charts/FanChart";
import { CaveatBanner } from "../components/CaveatBanner";
import { Card, SectionHeader } from "../components/Card";
import { Collapsible } from "../components/Collapsible";
import { EmptyState } from "../components/EmptyState";
import { ProjectionIcon } from "../components/icons";
import { PortfolioPicker } from "../components/PortfolioPicker";
import { ChartSkeleton, KpiGridSkeleton } from "../components/Skeleton";
import { startForRange } from "../lib/dates";
import { formatCurrency } from "../lib/format";
import { useShell } from "./shell-context";

export function Projection() {
  const { portfolios, openNew, selected } = useShell();
  const [chosenId, setChosenId] = useState<number | null>(null);
  const id =
    chosenId ?? selected?.id ?? (portfolios.length ? portfolios[0].id : null);
  const portfolio = portfolios.find((p) => p.id === id) ?? null;

  // Default start_value to the portfolio's latest simulated final value. We reuse
  // the existing simulate hook over a long window to recover that number.
  const simReq = useMemo<SimulateRequest | null>(
    () =>
      portfolio
        ? {
            spec: portfolio,
            start: startForRange("MAX"),
            benchmark: portfolio.benchmark_symbol,
          }
        : null,
    [portfolio],
  );
  const { data: sim, isLoading: simLoading } = useSimulation(simReq);

  const [years, setYears] = useState(20);
  const [goalOn, setGoalOn] = useState(false);
  const [goal, setGoal] = useState(1_000_000);
  const [startValue, setStartValue] = useState<number | null>(null);
  const [nPaths, setNPaths] = useState(2000);
  const [seed, setSeed] = useState(42);
  const [req, setReq] = useState<ProjectRequest | null>(null);

  // Prefill the (editable) start value once the simulation resolves, unless the
  // user has already typed one.
  const effectiveStart = startValue ?? (sim ? Math.round(sim.final_value) : null);

  const { data, isFetching, isError, error } = useProjection(req);

  useEffect(() => {
    if (isError) toast.error(apiErrorMessage(error, "Could not run the projection."));
  }, [isError, error]);

  function run() {
    if (!portfolio || effectiveStart == null) return;
    setReq({
      spec: portfolio,
      years,
      n_paths: nPaths,
      seed,
      goal: goalOn ? goal : null,
      start_value: effectiveStart,
      lookback_years: 10,
    });
  }

  if (portfolios.length === 0) {
    return (
      <div className="p-4 md:p-6">
        <Header />
        <div className="mt-4">
          <EmptyState
            icon={<ProjectionIcon size={40} />}
            title="No portfolios to project"
            message="Save a portfolio first, then project a range of possible future outcomes from its historical behavior."
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        {/* Controls */}
        <div className="flex flex-col gap-3 rounded-lg border border-edge bg-surface p-4 dark:border-edge-dark dark:bg-surface-dark">
          <PortfolioPicker
            portfolios={portfolios}
            value={id}
            onChange={(v) => {
              setChosenId(v);
              setStartValue(null); // re-derive from the new portfolio's sim
              setReq(null);
            }}
          />

          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Starting value
            </span>
            <input
              type="number"
              value={effectiveStart ?? ""}
              min={0}
              placeholder={simLoading ? "Loading…" : "0"}
              onChange={(e) =>
                // Empty input reverts to the auto-derived default (not $0).
                setStartValue(e.target.value === "" ? null : Number(e.target.value))
              }
              className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
            />
            <span className="mt-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Defaults to this portfolio&apos;s latest simulated value — editable.
            </span>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Horizon: {years} yr
            </span>
            <input
              type="range"
              min={1}
              max={40}
              value={years}
              onChange={(e) => setYears(Number(e.target.value))}
              className="w-full accent-brand"
            />
          </label>

          <div>
            <label className="mb-1 flex items-center gap-2 text-xs text-content-muted dark:text-content-dark-muted">
              <input
                type="checkbox"
                checked={goalOn}
                onChange={(e) => setGoalOn(e.target.checked)}
                className="h-4 w-4 accent-brand"
              />
              Set a goal ($)
            </label>
            <input
              type="number"
              value={goal}
              min={0}
              step={10000}
              disabled={!goalOn}
              onChange={(e) => setGoal(Number(e.target.value))}
              className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand disabled:opacity-50 dark:border-edge-dark dark:bg-surface-dark-alt"
            />
          </div>

          <Collapsible title="Advanced (paths / seed)">
            <div className="flex flex-col gap-3">
              <label className="block">
                <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                  Simulated paths: {nPaths.toLocaleString()}
                </span>
                <input
                  type="range"
                  min={500}
                  max={10000}
                  step={500}
                  value={nPaths}
                  onChange={(e) => setNPaths(Number(e.target.value))}
                  className="w-full accent-brand"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                  Random seed
                </span>
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(Number(e.target.value))}
                  className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
                />
              </label>
            </div>
          </Collapsible>

          <button
            onClick={run}
            disabled={isFetching || effectiveStart == null}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:opacity-60 dark:focus-visible:ring-offset-surface-dark"
          >
            {isFetching ? "Projecting…" : "Run projection"}
          </button>
        </div>

        {/* Results */}
        <div className="flex flex-col gap-4">
          {!req && !isFetching && (
            <EmptyState
              icon={<ProjectionIcon size={40} />}
              title="No projection yet"
              message="Pick a portfolio, choose a horizon, and run a Monte-Carlo projection of possible outcomes."
            />
          )}

          {isFetching && (
            <>
              <Card className="p-3">
                <ChartSkeleton />
              </Card>
              <KpiGridSkeleton count={3} />
            </>
          )}

          {isError && !isFetching && (
            <div className="rounded-lg border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
              {apiErrorMessage(error, "Could not run the projection.")}
            </div>
          )}

          {data && !isFetching && !isError && (
            <>
              <CaveatBanner>{data.caveat}</CaveatBanner>

              {data.goal_probability != null && req?.goal != null && (
                <Card className="p-5">
                  <p className="text-sm text-content-muted dark:text-content-dark-muted">
                    {/* Label from the EXECUTED request, not live slider state. */}
                    Probability of reaching {formatCurrency(req.goal)} in {req.years} years
                  </p>
                  <p className="mt-1 text-3xl font-semibold tabular-nums text-brand">
                    {Math.round(data.goal_probability * 100)}%
                  </p>
                </Card>
              )}

              <Card className="p-3">
                <FanChart bands={data.bands} contributed={data.contributed} />
              </Card>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Stat label="Pessimistic (5th pct)" value={data.terminal.p5} tone="down" />
                <Stat label="Median (50th pct)" value={data.terminal.p50} />
                <Stat label="Optimistic (95th pct)" value={data.terminal.p95} tone="up" />
              </div>

              <Card className="p-4">
                <SectionHeader>Terminal outcomes (all percentiles)</SectionHeader>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-5">
                  {(["p5", "p25", "p50", "p75", "p95"] as const).map((k) => (
                    <div key={k}>
                      <div className="text-xs text-content-muted dark:text-content-dark-muted">
                        {k.toUpperCase()}
                      </div>
                      <div className="font-semibold tabular-nums">
                        {formatCurrency(data.terminal[k])}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Header() {
  return (
    <div>
      <h1 className="text-xl font-semibold">Projection</h1>
      <p className="text-sm text-content-muted dark:text-content-dark-muted">
        Project a range of possible future outcomes for a saved portfolio using a
        Monte-Carlo simulation of its historical behavior.
      </p>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "up" | "down" | "neutral";
}) {
  const toneClass =
    tone === "up"
      ? "text-up"
      : tone === "down"
        ? "text-down"
        : "text-content dark:text-content-dark";
  return (
    <div className="rounded-xl border border-edge bg-surface-alt px-4 py-3 dark:border-edge-dark dark:bg-surface-dark-alt">
      <div className="text-xs text-content-muted dark:text-content-dark-muted">
        {label}
      </div>
      <div className={`mt-1 text-lg font-semibold tabular-nums ${toneClass}`}>
        {formatCurrency(value)}
      </div>
    </div>
  );
}
