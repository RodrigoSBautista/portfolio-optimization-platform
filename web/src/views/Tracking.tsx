import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiErrorMessage } from "../api/client";
import { useRefreshValuations, useValuations } from "../api/queries";
import type { DateValuePoint } from "../api/types";
import { MultiSeriesChart, type NamedSeries } from "../charts/MultiSeriesChart";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { RefreshIcon, TrackIcon } from "../components/icons";
import { ChartSkeleton } from "../components/Skeleton";
import { formatCurrency } from "../lib/format";
import { useShell } from "./shell-context";

export function Tracking() {
  const { portfolios, openNew, selected } = useShell();
  // Explicit user choice (null until they pick one). The effective selection
  // falls back to the shell's active portfolio, then the first one — derived at
  // render time so it stays valid even if portfolios load after mount.
  const [chosenId, setChosenId] = useState<number | null>(null);
  const id =
    chosenId ?? selected?.id ?? (portfolios.length ? portfolios[0].id : null);

  const { data, isLoading, isError, error } = useValuations(id);
  const refresh = useRefreshValuations();

  useEffect(() => {
    if (isError) toast.error(apiErrorMessage(error, "Could not load valuations."));
  }, [isError, error]);

  const valuations = useMemo(() => data?.valuations ?? [], [data]);

  const { portfolioSeries, benchmark } = useMemo(() => {
    const pf: DateValuePoint[] = valuations.map((v) => ({
      date: v.date,
      value: v.market_value,
    }));
    const bench = valuations
      .filter((v) => v.benchmark_value != null)
      .map((v) => ({ date: v.date, value: v.benchmark_value as number }));
    return {
      portfolioSeries: pf,
      benchmark: bench.length ? { label: "Benchmark", points: bench } : null,
    };
  }, [valuations]);

  const selectedPortfolio = portfolios.find((p) => p.id === id) ?? null;

  async function onRefresh() {
    if (id == null) return;
    try {
      const res = await refresh.mutateAsync({ id });
      toast.success(
        res.written > 0
          ? `Refreshed — ${res.written} row${res.written === 1 ? "" : "s"} written.`
          : "Already up to date — no new rows.",
      );
    } catch (err) {
      toast.error(apiErrorMessage(err, "Refresh failed."));
    }
  }

  if (portfolios.length === 0) {
    return (
      <div className="p-4 md:p-6">
        <Header />
        <div className="mt-4">
          <EmptyState
            icon={<TrackIcon size={40} />}
            title="No portfolios to track"
            message="Save a portfolio, then track its stored valuation history here against a benchmark."
            actionLabel="+ New portfolio"
            onAction={openNew}
          />
        </div>
      </div>
    );
  }

  const series: NamedSeries[] = [
    { key: "portfolio", label: selectedPortfolio?.name ?? "Portfolio", points: portfolioSeries },
  ];

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <Header />

      <Card className="flex flex-wrap items-end gap-3 p-4">
        <label className="block">
          <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
            Portfolio
          </span>
          <select
            value={id ?? ""}
            onChange={(e) => setChosenId(Number(e.target.value))}
            className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
          >
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={onRefresh}
          disabled={refresh.isPending || id == null}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-edge px-4 py-2 text-sm font-medium transition hover:bg-surface-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-50 dark:border-edge-dark dark:hover:bg-surface-dark-alt"
        >
          <RefreshIcon className={refresh.isPending ? "animate-spin" : ""} />
          {refresh.isPending ? "Refreshing…" : "Refresh now"}
        </button>
      </Card>

      {isLoading && (
        <Card className="p-3">
          <ChartSkeleton />
        </Card>
      )}

      {!isLoading && valuations.length === 0 && (
        <EmptyState
          icon={<TrackIcon size={40} />}
          title="No stored valuations yet"
          message="This portfolio has no tracked history. Run a first refresh to compute and store its daily valuations vs the benchmark."
          actionLabel={refresh.isPending ? "Refreshing…" : "Refresh now"}
          onAction={onRefresh}
        />
      )}

      {!isLoading && valuations.length > 0 && (
        <>
          <Card className="p-3">
            <MultiSeriesChart series={series} benchmark={benchmark} />
          </Card>
          <p className="text-xs text-content-muted dark:text-content-dark-muted">
            Tracked value includes your contributions, so it is not a pure return —
            see the Dashboard for return metrics.
          </p>
          {valuations.length > 0 && (
            <p className="text-xs text-content-muted dark:text-content-dark-muted">
              Latest tracked value:{" "}
              <span className="font-semibold tabular-nums text-content dark:text-content-dark">
                {formatCurrency(valuations[valuations.length - 1].market_value)}
              </span>{" "}
              on {valuations[valuations.length - 1].date}.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function Header() {
  return (
    <div>
      <h1 className="text-xl font-semibold">Tracking</h1>
      <p className="text-sm text-content-muted dark:text-content-dark-muted">
        Stored daily valuations for a saved portfolio vs its benchmark.
      </p>
    </div>
  );
}
