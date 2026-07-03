import type { CorrelationMatrix } from "../api/types";

interface Props {
  matrix: CorrelationMatrix;
}

// Diverging color for a correlation in [-1, 1]: blue (negative) -> neutral grey
// (0) -> red (positive). Cell numbers are always printed too, so the chart never
// relies on color alone (accessibility).
function divergingColor(v: number): string {
  const t = Math.max(-1, Math.min(1, v));
  if (t >= 0) {
    // 0 -> neutral grey (209,209,209), 1 -> red (209,36,47)
    const g = 209 * (1 - t) + 36 * t;
    const b = 209 * (1 - t) + 47 * t;
    return `rgb(209, ${Math.round(g)}, ${Math.round(b)})`;
  }
  // 0 -> neutral, -1 -> blue
  const a = -t;
  const r = 209 * (1 - a) + 26 * a;
  const g = 209 * (1 - a) + 115 * a;
  const b = 209 * (1 - a) + 232 * a;
  return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
}

// Choose readable text color against the cell background.
function textColor(v: number): string {
  return Math.abs(v) > 0.55 ? "#ffffff" : "#202124";
}

// Correlation heatmap: a labeled N×N grid (both axes labeled with tickers) using
// a diverging scale, with the correlation printed in each cell.
export function CorrelationHeatmap({ matrix }: Props) {
  const { tickers, values } = matrix;
  const n = tickers.length;
  if (!n) return null;

  return (
    <div className="overflow-x-auto">
      <div
        className="grid gap-px"
        style={{
          gridTemplateColumns: `minmax(3rem, auto) repeat(${n}, minmax(2.75rem, 1fr))`,
        }}
      >
        {/* Header row: empty corner + column tickers. */}
        <div />
        {tickers.map((t) => (
          <div
            key={`col-${t}`}
            className="px-1 py-1 text-center text-[11px] font-semibold text-content-muted dark:text-content-dark-muted"
          >
            {t}
          </div>
        ))}

        {/* Body rows. */}
        {tickers.map((rowT, i) => (
          <FragmentRow
            key={`row-${rowT}`}
            label={rowT}
            rowValues={values[i] ?? []}
          />
        ))}
      </div>

      <div className="mt-3 flex items-center gap-2 text-xs text-content-muted dark:text-content-dark-muted">
        <span>-1</span>
        <span
          className="h-2.5 w-32 rounded-sm"
          style={{
            background:
              "linear-gradient(to right, rgb(26,115,232), rgb(209,209,209), rgb(209,36,47))",
          }}
        />
        <span>+1</span>
        <span className="ml-1">correlation</span>
      </div>
    </div>
  );
}

function FragmentRow({
  label,
  rowValues,
}: {
  label: string;
  rowValues: number[];
}) {
  return (
    <>
      <div className="flex items-center px-1 py-1 text-right text-[11px] font-semibold text-content-muted dark:text-content-dark-muted">
        {label}
      </div>
      {rowValues.map((v, j) => (
        <div
          key={j}
          className="flex items-center justify-center py-2 text-[11px] font-medium tabular-nums"
          style={{ background: divergingColor(v), color: textColor(v) }}
          title={`${label} × col ${j + 1}: ${v.toFixed(2)}`}
        >
          {v.toFixed(2)}
        </div>
      ))}
    </>
  );
}
