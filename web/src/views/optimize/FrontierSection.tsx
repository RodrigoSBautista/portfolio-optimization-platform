import { useEffect, useMemo } from "react";
import { toast } from "sonner";
import { apiErrorMessage } from "../../api/client";
import { useFrontier } from "../../api/queries";
import type { FrontierRequest } from "../../api/types";
import { FrontierChart } from "../../charts/FrontierChart";
import { Card, SectionHeader } from "../../components/Card";
import { ChartSkeleton } from "../../components/Skeleton";

interface Props {
  // The universe the frontier is sampled over (the optimization's selected set).
  tickers: string[];
  // The suggested allocation, passed as a labeled marker via extra_points.
  suggested: Record<string, number>;
  lookbackYears: number;
  riskFreeRate: number; // annual fraction
}

// Efficient-frontier section shown under an optimization result: a cloud of
// random portfolios, the frontier line, and markers (Equal weight always, plus
// the suggested allocation). Fetches on its own once a result exists.
export function FrontierSection({
  tickers,
  suggested,
  lookbackYears,
  riskFreeRate,
}: Props) {
  const req = useMemo<FrontierRequest | null>(
    () =>
      tickers.length >= 2
        ? {
            tickers,
            lookback_years: lookbackYears,
            risk_free_rate: riskFreeRate,
            extra_points: [{ label: "Suggested", weights: suggested }],
          }
        : null,
    [tickers, lookbackYears, riskFreeRate, suggested],
  );

  const { data, isFetching, isError, error } = useFrontier(req);

  useEffect(() => {
    if (isError)
      toast.error(apiErrorMessage(error, "Could not compute the efficient frontier."));
  }, [isError, error]);

  return (
    <Card className="p-4">
      <SectionHeader>Efficient frontier</SectionHeader>
      {isFetching && <ChartSkeleton height={380} />}
      {isError && !isFetching && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
          {apiErrorMessage(error, "Could not compute the efficient frontier.")}
        </div>
      )}
      {data && !isFetching && !isError && (
        <>
          <FrontierChart data={data} />
          <p className="mt-2 text-xs text-content-muted dark:text-content-dark-muted">
            Each grey dot is a random long-only portfolio of the selected holdings.
            The line traces the best return for each level of risk; markers show the
            equal-weight and suggested allocations.
          </p>
        </>
      )}
    </Card>
  );
}
