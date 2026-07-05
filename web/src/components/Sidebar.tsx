import { NavLink } from "react-router-dom";
import { usePortfolios } from "../api/queries";
import type { Portfolio } from "../api/types";
import { BENCHMARK_INDICES } from "../lib/benchmarks";
import { isLotBased } from "../lib/lots";
import {
  ChartIcon,
  CompareIcon,
  DiversifyIcon,
  PlusIcon,
  ProjectionIcon,
  RetirementIcon,
  SparklesIcon,
  TrackIcon,
} from "./icons";
import { SidebarSkeleton } from "./Skeleton";
import { SidebarRow } from "./SidebarRow";

interface Props {
  selectedId: number | null;
  onSelect: (p: Portfolio) => void;
  onNew: () => void;
  // Fired on any navigation/selection so a mobile drawer can close itself.
  onNavigate?: () => void;
}

const NAV = [
  { to: "/", label: "Dashboard", icon: ChartIcon, end: true },
  { to: "/projection", label: "Projection", icon: ProjectionIcon, end: false },
  { to: "/retirement", label: "Retirement", icon: RetirementIcon, end: false },
  { to: "/optimize", label: "Optimize", icon: SparklesIcon, end: false },
  { to: "/diversification", label: "Diversification", icon: DiversifyIcon, end: false },
  { to: "/compare", label: "Compare", icon: CompareIcon, end: false },
  { to: "/tracking", label: "Tracking", icon: TrackIcon, end: false },
] as const;

// Shared sidebar contents (used by both the fixed desktop rail and the mobile
// drawer). Top nav uses NavLink with an active accent bar; below it, the user's
// portfolios (with sparklines) and benchmark indices.
export function Sidebar({ selectedId, onSelect, onNew, onNavigate }: Props) {
  const { data: portfolios = [], isLoading } = usePortfolios();

  return (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <button
          onClick={() => {
            onNew();
            onNavigate?.();
          }}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-sm font-medium text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface-alt dark:focus-visible:ring-offset-surface-dark-alt"
        >
          <PlusIcon size={16} /> New portfolio
        </button>
      </div>

      <nav className="px-2 pb-2">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                isActive
                  ? "bg-brand/10 text-brand"
                  : "text-content-muted hover:bg-surface hover:text-content dark:text-content-dark-muted dark:hover:bg-surface-dark dark:hover:text-content-dark"
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-brand" />
                )}
                <Icon size={17} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        <SectionLabel>Your portfolios</SectionLabel>
        {isLoading && <SidebarSkeleton />}
        {!isLoading && portfolios.length === 0 && (
          <div className="px-2 py-2 text-sm text-content-muted dark:text-content-dark-muted">
            No portfolios yet. Create one to get started.
          </div>
        )}
        {portfolios.map((p) => (
          <SidebarRow
            key={p.id}
            id={p.id}
            label={p.name}
            sublabel={`${
              isLotBased(p)
                ? `${p.lots!.length} purchase${p.lots!.length === 1 ? "" : "s"}`
                : `${p.holdings.length} holding${p.holdings.length === 1 ? "" : "s"}`
            } · vs ${p.benchmark_symbol}`}
            spec={p}
            active={selectedId === p.id}
            onClick={() => {
              onSelect(p);
              onNavigate?.();
            }}
          />
        ))}

        <SectionLabel className="mt-4">Indices</SectionLabel>
        {BENCHMARK_INDICES.map((b) => (
          <SidebarRow
            key={b.symbol}
            id={`idx-${b.symbol}`}
            label={b.name}
            sublabel="Benchmark index"
            spec={b.spec}
          />
        ))}
      </div>
    </div>
  );
}

function SectionLabel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`px-2 py-1 text-xs font-semibold uppercase tracking-wide text-content-muted dark:text-content-dark-muted ${className}`}
    >
      {children}
    </div>
  );
}
