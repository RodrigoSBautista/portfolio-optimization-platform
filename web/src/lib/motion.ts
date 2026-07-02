import type { Variants } from "framer-motion";

// Shared motion variants. All motion is opt-in and callers gate it behind
// framer's `useReducedMotion()` (pass reduced -> use the `none`/instant variant).

// Container that staggers its children's entrance (KPI cards, sections).
export const staggerContainer: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.06, delayChildren: 0.02 },
  },
};

// A single item that fades + rises into place.
export const riseItem: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: "easeOut" } },
};

// Cross-fade used for the chart when the time range (or data) changes.
export const crossFade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.25 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

// Route-level transition for AnimatePresence.
export const pageTransition: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: { duration: 0.22, ease: "easeOut" } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.15 } },
};
