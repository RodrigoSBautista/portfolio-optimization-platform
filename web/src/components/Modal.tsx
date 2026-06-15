interface Props {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ title, onClose, children }: Props) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-lg border border-edge bg-surface shadow-xl dark:border-edge-dark dark:bg-surface-dark"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-edge px-4 py-3 dark:border-edge-dark">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-content-muted hover:bg-surface-alt dark:text-content-dark-muted dark:hover:bg-surface-dark-alt"
          >
            ✕
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}
