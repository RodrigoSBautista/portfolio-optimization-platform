import { useEffect } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { CloseIcon } from "./icons";

interface Props {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ title, onClose, children }: Props) {
  const reduce = useReducedMotion();

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      onClick={onClose}
      role="dialog"
      aria-modal
      aria-label={title}
    >
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: reduce ? 0 : 0.2, ease: "easeOut" }}
        className="w-full max-w-2xl rounded-xl border border-edge bg-surface shadow-xl dark:border-edge-dark dark:bg-surface-dark"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-edge px-4 py-3 dark:border-edge-dark">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1 text-content-muted hover:bg-surface-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand dark:text-content-dark-muted dark:hover:bg-surface-dark-alt"
          >
            <CloseIcon size={18} />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </motion.div>
    </div>
  );
}
