import { EmptyState } from "../components/EmptyState";
import { FolderIcon } from "../components/icons";
import { Dashboard } from "./Dashboard";
import { useShell } from "./shell-context";

// Route wrapper for the dashboard: shows the active portfolio or an empty state.
export function DashboardPage() {
  const { selected, openNew, deletePortfolio } = useShell();
  if (!selected) {
    return (
      <div className="p-4 md:p-6">
        <EmptyState
          icon={<FolderIcon />}
          title="No portfolios yet"
          message="Create your first portfolio to simulate how it would have grown vs a benchmark."
          actionLabel="+ New portfolio"
          onAction={openNew}
        />
      </div>
    );
  }
  return (
    <Dashboard portfolio={selected} onDelete={() => deletePortfolio(selected)} />
  );
}
