import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { toast } from "sonner";
import { useDeletePortfolio, usePortfolios } from "../api/queries";
import type { Portfolio } from "../api/types";
import { Disclaimer } from "../components/Disclaimer";
import { MobileDrawer } from "../components/MobileDrawer";
import { Modal } from "../components/Modal";
import { Sidebar } from "../components/Sidebar";
import { TopBar } from "../components/TopBar";
import { pageTransition } from "../lib/motion";
import { NewPortfolio } from "./NewPortfolio";
import type { ShellContext } from "./shell-context";

// Prefill for the "Save as portfolio" flow coming from the Optimize view.
interface Seed {
  weights: Record<string, number>;
  benchmark: string;
}

// Persistent app chrome (top bar + sidebar/drawer) around the routed views.
export function Layout() {
  const { data: portfolios = [] } = usePortfolios();
  const del = useDeletePortfolio();
  const [selected, setSelected] = useState<Portfolio | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [seed, setSeed] = useState<Seed | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const reduce = useReducedMotion();

  // The portfolio to show: explicit selection, else the first one.
  const active = selected ?? portfolios[0] ?? null;

  // Close the mobile drawer on any route change (covers browser back/forward and
  // any link that doesn't route through onNavigate). Syncing this transient UI
  // flag to the current route is a legitimate effect.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setDrawerOpen(false), [location.pathname]);

  function openNew() {
    setSeed(null);
    setShowNew(true);
  }

  function openNewSeeded(weights: Record<string, number>, benchmark: string) {
    setSeed({ weights, benchmark });
    setShowNew(true);
  }

  function handleCreated(p: Portfolio) {
    setShowNew(false);
    setSeed(null);
    setSelected(p);
    toast.success(`Saved "${p.name}"`);
    navigate("/");
  }

  const ctx: ShellContext = {
    portfolios,
    selected: active,
    selectPortfolio: (p) => {
      setSelected(p);
      navigate("/");
    },
    openNew,
    openNewSeeded,
    deletePortfolio: async (p) => {
      try {
        await del.mutateAsync(p.id);
        if (selected?.id === p.id) setSelected(null);
        toast.success(`Deleted "${p.name}"`);
        navigate("/");
      } catch {
        toast.error("Could not delete the portfolio.");
      }
    },
  };

  const sidebar = (
    <Sidebar
      selectedId={location.pathname === "/" ? (active?.id ?? null) : null}
      onSelect={(p) => setSelected(p)}
      onNew={openNew}
      onNavigate={() => setDrawerOpen(false)}
    />
  );

  return (
    <div className="flex h-full flex-col">
      <TopBar onMenu={() => setDrawerOpen(true)} />
      <div className="flex min-h-0 flex-1">
        {/* Desktop rail */}
        <aside className="hidden w-72 shrink-0 border-r border-edge bg-surface-alt lg:block dark:border-edge-dark dark:bg-surface-dark-alt">
          {sidebar}
        </aside>

        {/* Mobile drawer */}
        <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
          {sidebar}
        </MobileDrawer>

        <main className="min-w-0 flex-1 overflow-y-auto">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              variants={reduce ? undefined : pageTransition}
              initial={reduce ? false : "hidden"}
              animate={reduce ? undefined : "show"}
              exit={reduce ? undefined : "exit"}
              className="h-full"
            >
              <Outlet context={ctx} />
            </motion.div>
          </AnimatePresence>
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
