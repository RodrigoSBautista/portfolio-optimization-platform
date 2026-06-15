import { useMemo, useState } from "react";
import { useTickers } from "../api/queries";

interface Props {
  onSelect: (symbol: string) => void;
  exclude?: string[];
  placeholder?: string;
}

// Typeahead over /api/tickers. Filters client-side (the universe is ~540 rows).
export function TickerSearch({ onSelect, exclude = [], placeholder }: Props) {
  const { data: tickers = [], isLoading } = useTickers();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const matches = useMemo(() => {
    const q = query.trim().toUpperCase();
    if (!q) return [];
    const ex = new Set(exclude.map((e) => e.toUpperCase()));
    return tickers
      .filter(
        (t) =>
          !ex.has(t.symbol.toUpperCase()) &&
          (t.symbol.toUpperCase().includes(q) ||
            t.name.toUpperCase().includes(q)),
      )
      .slice(0, 8);
  }, [query, tickers, exclude]);

  function pick(symbol: string) {
    onSelect(symbol);
    setQuery("");
    setOpen(false);
  }

  return (
    <div className="relative">
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        placeholder={isLoading ? "Loading tickers…" : (placeholder ?? "Search ticker or name…")}
        className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark-alt"
      />
      {open && matches.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border border-edge bg-surface shadow-lg dark:border-edge-dark dark:bg-surface-dark-alt">
          {matches.map((t) => (
            <li key={t.symbol}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(t.symbol)}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-surface-alt dark:hover:bg-surface-dark"
              >
                <span className="font-medium">{t.symbol}</span>
                <span className="ml-3 truncate text-content-muted dark:text-content-dark-muted">
                  {t.name}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
