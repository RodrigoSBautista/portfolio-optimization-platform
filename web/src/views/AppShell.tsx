import { useState } from "react";
import { usePortfolios } from "../api/queries";
import type { Portfolio } from "../api/types";
import { Disclaimer } from "../components/Disclaimer";
import { Modal } from "../components/Modal";
import { Sidebar } from "../components/Sidebar";
import { TopBar } from "../components/TopBar";
import { Dashboard } from "./Dashboard";
import { NewPortfolio } from "./NewPortfolio";
import { Optimize } from "./Optimize";

type MainView = "dashboard" | "optimize";

// Prefill for the "Save as portfolio" flow coming from the Optimize view.
interface Seed {
  weights: Record<string, number>;
  benchmark: string;
}

export function AppShell() {
  const { data: portfolios = [] } = usePortfolios();
  const [selected, setSelected] = useState<Portfolio | null>(null);
  const [view, setView] = useState<MainView>("dashboard");
  const [showNew, setShowNew] = useState(false);
  const [seed, setSeed] = useState<Seed | null>(null);

  // The portfolio to show: explicit selection, else the first one.
  const active = selected ?? portfolios[0] ?? null;

  function openNew() {
    setSeed(null);
    setShowNew(true);
  }

  function handleCreated(p: Portfolio) {
    setShowNew(false);
    setSeed(null);
    setSelected(p);
    setView("dashboard");
  }

  return (
    <div className="flex h-full flex-col">
      <TopBar />
      <div className="flex min-h-0 flex-1">
        <Sidebar
          selectedId={view === "dashboard" ? (active?.id ?? null) : null}
          onSelect={(p) => {
            setSelected(p);
            setView("dashboard");
          }}
          onNew={openNew}
          onOptimize={() => setView("optimize")}
        />

        <main className="min-w-0 flex-1 overflow-y-auto">
          {view === "optimize" ? (
            <Optimize
              onSaveAsPortfolio={(weights, benchmark) => {
                setSeed({ weights, benchmark });
                setShowNew(true);
              }}
            />
          ) : active ? (
            <Dashboard portfolio={active} />
          ) : (
            <EmptyState onNew={openNew} />
          )}
        </main>
      </div>
      <Disclaimer />

      {showNew && (
        <Modal title="New portfolio" onClose={() => setShowNew(false)}>
          <NewPortfolio
            onCreated={handleCreated}
            onCancel={() => setShowNew(false)}
            initialWeights={seed?.weights}
            initialBenchmark={seed?.benchmark}
            initialName={seed ? "Optimized portfolio" : undefined}
          />
        </Modal>
      )}
    </div>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <h2 className="text-lg font-semibold">No portfolio selected</h2>
      <p className="max-w-sm text-sm text-content-muted dark:text-content-dark-muted">
        Create your first portfolio to simulate how it would have grown.
      </p>
      <button
        onClick={onNew}
        className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90"
      >
        + New portfolio
      </button>
    </div>
  );
}
