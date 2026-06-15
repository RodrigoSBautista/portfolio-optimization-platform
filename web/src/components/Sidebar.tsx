import { usePortfolios } from "../api/queries";
import type { Portfolio } from "../api/types";
import { BENCHMARK_INDICES } from "../lib/benchmarks";
import { SidebarRow } from "./SidebarRow";

interface Props {
  selectedId: number | null;
  onSelect: (p: Portfolio) => void;
  onNew: () => void;
  onOptimize: () => void;
}

export function Sidebar({ selectedId, onSelect, onNew, onOptimize }: Props) {
  const { data: portfolios = [], isLoading } = usePortfolios();

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-edge bg-surface-alt dark:border-edge-dark dark:bg-surface-dark-alt">
      <div className="flex items-center gap-2 p-3">
        <button
          onClick={onNew}
          className="flex-1 rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          + New portfolio
        </button>
        <button
          onClick={onOptimize}
          className="rounded-md border border-edge px-3 py-2 text-sm font-medium hover:bg-surface dark:border-edge-dark dark:hover:bg-surface-dark"
        >
          Optimize
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-3">
        <SectionLabel>Your portfolios</SectionLabel>
        {isLoading && (
          <div className="px-2 py-2 text-sm text-content-muted dark:text-content-dark-muted">
            Loading…
          </div>
        )}
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
            sublabel={`${p.holdings.length} holdings · vs ${p.benchmark_symbol}`}
            spec={p}
            active={selectedId === p.id}
            onClick={() => onSelect(p)}
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
      </nav>
    </aside>
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
