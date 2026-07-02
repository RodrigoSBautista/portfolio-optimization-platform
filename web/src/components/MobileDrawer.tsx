import { useEffect } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { CloseIcon } from "./icons";

interface Props {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

// Slide-in navigation drawer for small screens (< lg). Backdrop click, the close
// button, and Escape all dismiss it. Motion respects reduced-motion.
export function MobileDrawer({ open, onClose, children }: Props) {
  const reduce = useReducedMotion();

  // Close on Escape while open.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-40 lg:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduce ? 0 : 0.15 }}
        >
          <div
            className="absolute inset-0 bg-black/40"
            onClick={onClose}
            aria-hidden
          />
          <motion.aside
            className="absolute inset-y-0 left-0 flex w-72 max-w-[80vw] flex-col border-r border-edge bg-surface-alt shadow-xl dark:border-edge-dark dark:bg-surface-dark-alt"
            role="dialog"
            aria-label="Navigation"
            initial={{ x: reduce ? 0 : "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: reduce ? 0 : "-100%" }}
            transition={{ duration: reduce ? 0 : 0.22, ease: "easeOut" }}
          >
            <div className="flex justify-end p-2">
              <button
                onClick={onClose}
                aria-label="Close navigation"
                className="rounded-lg p-2 text-content-muted hover:bg-surface hover:text-content focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand dark:text-content-dark-muted dark:hover:bg-surface-dark"
              >
                <CloseIcon />
              </button>
            </div>
            <div className="min-h-0 flex-1">{children}</div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
