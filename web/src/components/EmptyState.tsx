interface Props {
  icon: React.ReactNode;
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

// A friendly empty state: centered icon + title + message + optional CTA button.
export function EmptyState({ icon, title, message, actionLabel, onAction }: Props) {
  return (
    <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-edge p-8 text-center dark:border-edge-dark">
      <div className="text-content-muted dark:text-content-dark-muted">{icon}</div>
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="max-w-sm text-sm text-content-muted dark:text-content-dark-muted">
        {message}
      </p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-1 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface dark:focus-visible:ring-offset-surface-dark"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
