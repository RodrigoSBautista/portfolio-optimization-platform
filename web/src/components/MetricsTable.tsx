import type { Metrics } from "../api/types";

// Renders the preformatted metric strings as a table: rows = metric names,
// columns = each series (portfolio / benchmark / methods).
export function MetricsTable({ metrics }: { metrics: Metrics }) {
  const columns = Object.keys(metrics);
  if (!columns.length) return null;
  // Union of metric names across all columns, preserving first-seen order.
  const rowNames: string[] = [];
  for (const col of columns) {
    for (const name of Object.keys(metrics[col])) {
      if (!rowNames.includes(name)) rowNames.push(name);
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-edge text-left text-content-muted dark:border-edge-dark dark:text-content-dark-muted">
            <th className="py-2 pr-4 font-medium">Metric</th>
            {columns.map((c) => (
              <th key={c} className="py-2 pr-4 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowNames.map((name) => (
            <tr
              key={name}
              className="border-b border-edge/60 dark:border-edge-dark/60"
            >
              <td className="py-2 pr-4 text-content-muted dark:text-content-dark-muted">
                {name}
              </td>
              {columns.map((c) => (
                <td key={c} className="py-2 pr-4 tabular-nums">
                  {metrics[c][name] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
