// Reusable shimmer skeleton loaders. A base <Skeleton> block plus a few composed
// shapes (chart, KPI cards, metrics rows, sidebar rows) so every loading state
// shares one look instead of plain "loading…" text.

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

// Base shimmering block. The moving highlight is a translated gradient overlay
// (Tailwind `animate-shimmer`); the base tint uses the theme's alt surface.
export function Skeleton({ className = "", style }: SkeletonProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-md bg-surface-alt dark:bg-surface-dark-alt ${className}`}
      style={style}
      aria-hidden
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-black/5 to-transparent dark:via-white/5" />
    </div>
  );
}

// Chart placeholder: a tall block with a small legend row above it.
export function ChartSkeleton({ height = 340 }: { height?: number }) {
  return (
    <div className="flex flex-col gap-3" role="status" aria-label="Loading chart">
      <div className="flex gap-2">
        <Skeleton className="h-6 w-24 rounded-full" />
        <Skeleton className="h-6 w-24 rounded-full" />
      </div>
      <Skeleton className="w-full rounded-xl" style={{ height }} />
    </div>
  );
}

// KPI grid placeholder: a matching responsive grid of tile skeletons.
export function KpiGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div
      className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
      role="status"
      aria-label="Loading metrics"
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl border border-edge bg-surface-alt px-4 py-3 dark:border-edge-dark dark:bg-surface-dark-alt"
        >
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-2 h-6 w-20" />
        </div>
      ))}
    </div>
  );
}

// Metrics-table placeholder: header + a few striped rows.
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2" role="status" aria-label="Loading table">
      <Skeleton className="h-5 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full opacity-80" />
      ))}
    </div>
  );
}

// Sidebar rows placeholder.
export function SidebarSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-1 px-2" role="status" aria-label="Loading portfolios">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-2 px-2 py-2">
          <div className="min-w-0 flex-1">
            <Skeleton className="h-3.5 w-28" />
            <Skeleton className="mt-1.5 h-3 w-20" />
          </div>
          <Skeleton className="h-7 w-16 shrink-0" />
        </div>
      ))}
    </div>
  );
}
