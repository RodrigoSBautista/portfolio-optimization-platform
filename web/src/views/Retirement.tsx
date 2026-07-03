import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiErrorMessage } from "../api/client";
import { useRetirement } from "../api/queries";
import type { RetirementRequest, WithdrawalKind } from "../api/types";
import { FanChart } from "../charts/FanChart";
import { CaveatBanner } from "../components/CaveatBanner";
import { Card, SectionHeader } from "../components/Card";
import { Collapsible } from "../components/Collapsible";
import { EmptyState } from "../components/EmptyState";
import { RetirementIcon } from "../components/icons";
import { PortfolioPicker } from "../components/PortfolioPicker";
import { ChartSkeleton } from "../components/Skeleton";
import { useShell } from "./shell-context";

export function Retirement() {
  const { portfolios, openNew, selected } = useShell();
  const [chosenId, setChosenId] = useState<number | null>(null);
  const id =
    chosenId ?? selected?.id ?? (portfolios.length ? portfolios[0].id : null);
  const portfolio = portfolios.find((p) => p.id === id) ?? null;

  const [startBalance, setStartBalance] = useState(1_000_000);
  const [years, setYears] = useState(30);
  const [kind, setKind] = useState<WithdrawalKind>("fixed");
  const [amount, setAmount] = useState(4000); // $/mo
  const [ratePct, setRatePct] = useState(4); // annual %
  const [inflationPct, setInflationPct] = useState(2.5);
  const [nPaths, setNPaths] = useState(2000);
  const [seed, setSeed] = useState(42);
  const [req, setReq] = useState<RetirementRequest | null>(null);

  const { data, isFetching, isError, error } = useRetirement(req);

  useEffect(() => {
    if (isError)
      toast.error(apiErrorMessage(error, "Could not run the retirement simulation."));
  }, [isError, error]);

  function run() {
    if (!portfolio) return;
    setReq({
      spec: portfolio,
      start_balance: startBalance,
      years,
      withdrawal:
        kind === "fixed"
          ? { kind: "fixed", amount }
          : { kind: "rate", rate: ratePct / 100 },
      inflation_pct: inflationPct,
      n_paths: nPaths,
      seed,
      lookback_years: 10,
    });
  }

  if (portfolios.length === 0) {
    return (
      <div className="p-4 md:p-6">
        <Header />
        <div className="mt-4">
          <EmptyState
            icon={<RetirementIcon size={40} />}
            title="No portfolios to draw from"
            message="Save a portfolio to use as the return engine, then test how long it could sustain your withdrawals."
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
            label="Return engine (portfolio)"
            onChange={(v) => {
              setChosenId(v);
              setReq(null);
            }}
          />

          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Starting balance
            </span>
            <input
              type="number"
              value={startBalance}
              min={0}
              step={10000}
              onChange={(e) => setStartBalance(Number(e.target.value))}
              className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Years in retirement: {years}
            </span>
            <input
              type="range"
              min={5}
              max={50}
              value={years}
              onChange={(e) => setYears(Number(e.target.value))}
              className="w-full accent-brand"
            />
          </label>

          {/* Withdrawal mode toggle */}
          <div>
            <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
              Withdrawal
            </span>
            <div className="flex gap-1 rounded-md border border-edge p-1 dark:border-edge-dark">
              {(
                [
                  ["fixed", "Fixed $/mo"],
                  ["rate", "Annual %"],
                ] as [WithdrawalKind, string][]
              ).map(([k, lbl]) => (
                <button
                  key={k}
                  onClick={() => setKind(k)}
                  className={`flex-1 rounded px-3 py-1.5 text-sm font-medium ${
                    kind === k
                      ? "bg-brand text-white"
                      : "text-content-muted hover:text-content dark:text-content-dark-muted"
                  }`}
                >
                  {lbl}
                </button>
              ))}
            </div>
          </div>

          {kind === "fixed" ? (
            <>
              <label className="block">
                <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                  Monthly withdrawal ($)
                </span>
                <input
                  type="number"
                  value={amount}
                  min={0}
                  step={100}
                  onChange={(e) => setAmount(Number(e.target.value))}
                  className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                  Grow withdrawals with inflation: {inflationPct}%/yr
                </span>
                <input
                  type="range"
                  min={0}
                  max={6}
                  step={0.1}
                  value={inflationPct}
                  onChange={(e) => setInflationPct(Number(e.target.value))}
                  className="w-full accent-brand"
                />
              </label>
            </>
          ) : (
            <label className="block">
              <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                Annual withdrawal rate: {ratePct}%
              </span>
              <input
                type="range"
                min={1}
                max={10}
                step={0.25}
                value={ratePct}
                onChange={(e) => setRatePct(Number(e.target.value))}
                className="w-full accent-brand"
              />
            </label>
          )}

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
            disabled={isFetching}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:opacity-60 dark:focus-visible:ring-offset-surface-dark"
          >
            {isFetching ? "Simulating…" : "Run simulation"}
          </button>
        </div>

        {/* Results */}
        <div className="flex flex-col gap-4">
          {!req && !isFetching && (
            <EmptyState
              icon={<RetirementIcon size={40} />}
              title="No simulation yet"
              message="Set a starting balance and a withdrawal plan, then simulate how often the money lasts the full horizon."
            />
          )}

          {isFetching && (
            <>
              <Card className="p-5">
                <ChartSkeleton height={80} />
              </Card>
              <Card className="p-3">
                <ChartSkeleton />
              </Card>
            </>
          )}

          {isError && !isFetching && (
            <div className="rounded-lg border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
              {apiErrorMessage(error, "Could not run the retirement simulation.")}
            </div>
          )}

          {data && !isFetching && !isError && (
            <>
              <CaveatBanner>{data.caveat}</CaveatBanner>

              <SuccessRateCard rate={data.success_rate} years={years} />

              <Card className="p-3">
                <SectionHeader>Projected balance over retirement</SectionHeader>
                <FanChart bands={data.bands} />
              </Card>

              <Card className="p-4">
                <SectionHeader>How long the money lasts (years)</SectionHeader>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-5">
                  {(["p5", "p25", "p50", "p75", "p95"] as const).map((k) => (
                    <div key={k}>
                      <div className="text-xs text-content-muted dark:text-content-dark-muted">
                        {k.toUpperCase()}
                      </div>
                      <div className="font-semibold tabular-nums">
                        {data.years_lasted[k].toFixed(1)} yr
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
      <h1 className="text-xl font-semibold">Retirement</h1>
      <p className="text-sm text-content-muted dark:text-content-dark-muted">
        Test whether a starting balance and a withdrawal plan survive a full
        retirement horizon, across many simulated return paths.
      </p>
    </div>
  );
}

// Big success-rate stat: green >= 90%, amber 70–90%, red < 70%.
function SuccessRateCard({ rate, years }: { rate: number; years: number }) {
  const pct = Math.round(rate * 100);
  const tone =
    pct >= 90
      ? { text: "text-up", ring: "border-up/40 bg-up/10" }
      : pct >= 70
        ? { text: "text-amber-600 dark:text-amber-400", ring: "border-amber-400/40 bg-amber-400/10" }
        : { text: "text-down", ring: "border-down/40 bg-down/10" };
  return (
    <Card className={`border ${tone.ring} p-5`}>
      <p className="text-sm text-content-muted dark:text-content-dark-muted">
        Success rate — money lasts the full {years} years
      </p>
      <p className={`mt-1 text-4xl font-semibold tabular-nums ${tone.text}`}>{pct}%</p>
    </Card>
  );
}
