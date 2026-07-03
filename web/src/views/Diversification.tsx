import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiErrorMessage } from "../api/client";
import { useDiversification } from "../api/queries";
import type { DiversificationRequest } from "../api/types";
import { CorrelationHeatmap } from "../charts/CorrelationHeatmap";
import { RiskContributionBar } from "../charts/RiskContributionBar";
import { Card, SectionHeader } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { DiversifyIcon } from "../components/icons";
import { PortfolioPicker } from "../components/PortfolioPicker";
import { ChartSkeleton } from "../components/Skeleton";
import { seriesColor } from "../theme/colors";
import { useShell } from "./shell-context";

export function Diversification() {
  const { portfolios, openNew, selected } = useShell();
  const [chosenId, setChosenId] = useState<number | null>(null);
  const id =
    chosenId ?? selected?.id ?? (portfolios.length ? portfolios[0].id : null);
  const portfolio = portfolios.find((p) => p.id === id) ?? null;

  // Build the request from the saved portfolio's holdings + weights. The heatmap
  // uses all holdings; risk contributions use the saved weights (the backend
  // falls back to equal-weight if weights are omitted).
  const req = useMemo<DiversificationRequest | null>(() => {
    if (!portfolio || portfolio.holdings.length < 2) return null;
    const weights: Record<string, number> = {};
    for (const h of portfolio.holdings) weights[h.symbol] = h.weight;
    return {
      tickers: portfolio.holdings.map((h) => h.symbol),
      lookback_years: 5,
      weights,
    };
  }, [portfolio]);

  const { data, isLoading, isError, error } = useDiversification(req);

  useEffect(() => {
    if (isError)
      toast.error(apiErrorMessage(error, "Could not analyze diversification."));
  }, [isError, error]);

  if (portfolios.length === 0) {
    return (
      <div className="p-4 md:p-6">
        <Header />
        <div className="mt-4">
          <EmptyState
            icon={<DiversifyIcon size={40} />}
            title="No portfolios to analyze"
            message="Save a portfolio with a few holdings, then see how correlated they are and where its risk concentrates."
            actionLabel="+ New portfolio"
            onAction={openNew}
          />
        </div>
      </div>
    );
  }

  const tooFew = portfolio != null && portfolio.holdings.length < 2;

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <Header />

      <Card className="flex flex-wrap items-end gap-3 p-4">
        <div className="min-w-[220px]">
          <PortfolioPicker
            portfolios={portfolios}
            value={id}
            onChange={(v) => setChosenId(v)}
          />
        </div>
        {portfolio && (
          <p className="text-xs text-content-muted dark:text-content-dark-muted">
            {portfolio.holdings.length} holdings · risk split uses the saved weights.
          </p>
        )}
      </Card>

      {tooFew && (
        <EmptyState
          icon={<DiversifyIcon size={40} />}
          title="Need at least two holdings"
          message="Diversification analysis compares how holdings move together. Add another holding to this portfolio."
        />
      )}

      {!tooFew && isLoading && (
        <>
          <Card className="p-4">
            <SectionHeader>Correlation</SectionHeader>
            <ChartSkeleton height={280} />
          </Card>
          <Card className="p-4">
            <SectionHeader>Risk contribution</SectionHeader>
            <ChartSkeleton height={220} />
          </Card>
        </>
      )}

      {!tooFew && isError && !isLoading && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
          {apiErrorMessage(error, "Could not analyze diversification.")}
        </div>
      )}

      {!tooFew && data && !isLoading && !isError && (
        <>
          <Card className="p-4">
            <SectionHeader>Correlation matrix</SectionHeader>
            <CorrelationHeatmap matrix={data.matrix} />
            <p className="mt-2 text-xs text-content-muted dark:text-content-dark-muted">
              Higher (red) means the two holdings tend to move together — less
              diversification benefit. Lower or negative (blue) holdings offset
              each other.
            </p>
          </Card>

          {data.clusters.length > 0 && (
            <Card className="p-4">
              <SectionHeader>Clusters</SectionHeader>
              <p className="mb-3 text-xs text-content-muted dark:text-content-dark-muted">
                Holdings that behave similarly are grouped — spreading across
                clusters diversifies more than adding names within one.
              </p>
              <div className="flex flex-col gap-3">
                {data.clusters.map((c, i) => (
                  <div key={c.label} className="flex flex-wrap items-center gap-2">
                    <span
                      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold text-white"
                      style={{ background: seriesColor(i) }}
                    >
                      {c.label}
                    </span>
                    {c.members.map((m) => (
                      <span
                        key={m}
                        className="rounded-full border border-edge bg-surface-alt px-2.5 py-1 text-xs dark:border-edge-dark dark:bg-surface-dark-alt"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card className="p-4">
            <SectionHeader>Risk contribution (% of portfolio risk)</SectionHeader>
            <RiskContributionBar contributions={data.risk_contributions} />
            <p className="mt-2 text-xs text-content-muted dark:text-content-dark-muted">
              Share of total portfolio volatility from each holding. A holding can
              carry more risk than its weight suggests if it is volatile or highly
              correlated with the rest.
            </p>
          </Card>
        </>
      )}
    </div>
  );
}

function Header() {
  return (
    <div>
      <h1 className="text-xl font-semibold">Diversification</h1>
      <p className="text-sm text-content-muted dark:text-content-dark-muted">
        See how a saved portfolio&apos;s holdings correlate, how they cluster, and
        where its risk concentrates.
      </p>
    </div>
  );
}
