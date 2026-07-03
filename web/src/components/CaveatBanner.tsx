interface Props {
  children: React.ReactNode;
}

// A prominent, high-visibility caveat banner for model-driven projections
// (Monte Carlo, retirement). Renders the API's caveat string. This is distinct
// from the global "Not financial advice" footer — it carries the specific
// modeling assumptions/limits the backend returns.
export function CaveatBanner({ children }: Props) {
  return (
    <div
      role="note"
      className="flex items-start gap-3 rounded-lg border border-amber-400/50 bg-amber-400/10 px-4 py-3 text-sm text-amber-800 dark:border-amber-300/30 dark:text-amber-200"
    >
      <svg
        width={18}
        height={18}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="mt-0.5 shrink-0"
        aria-hidden
      >
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <path d="M12 9v4M12 17h.01" />
      </svg>
      <p className="leading-relaxed">{children}</p>
    </div>
  );
}
