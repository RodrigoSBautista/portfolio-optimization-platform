import { Optimize } from "./Optimize";
import { useShell } from "./shell-context";

// Route wrapper: wires the Optimize view's "Save as portfolio" to the shell's
// seeded New-portfolio modal.
export function OptimizePage() {
  const { openNewSeeded } = useShell();
  return <Optimize onSaveAsPortfolio={openNewSeeded} />;
}
