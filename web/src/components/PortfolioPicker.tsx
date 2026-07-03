import type { Portfolio } from "../api/types";

interface Props {
  portfolios: Portfolio[];
  value: number | null;
  onChange: (id: number) => void;
  label?: string;
}

// A labeled <select> over the user's saved portfolios. Shared by the Projection
// and Retirement views (which drive their return engine from a saved portfolio).
export function PortfolioPicker({
  portfolios,
  value,
  onChange,
  label = "Portfolio",
}: Props) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
        {label}
      </span>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
      >
        {portfolios.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
    </label>
  );
}
