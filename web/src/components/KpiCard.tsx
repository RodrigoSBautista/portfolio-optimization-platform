import { motion, useReducedMotion } from "framer-motion";
import { CountUp } from "./CountUp";
import { riseItem } from "../lib/motion";

interface Props {
  label: string;
  // Either a preformatted string (e.g. TWR "12.3%") rendered verbatim, or a raw
  // number that animates via CountUp using `format`.
  value: string;
  tone?: "up" | "down" | "neutral";
  // When provided, the tile count-ups this number through `format` instead of
  // rendering `value`. Preformatted percentage strings must NOT use this.
  countTo?: number;
  format?: (n: number) => string;
}

// A single KPI tile: soft surface, gentle hover lift, staggered entrance (as an
// item inside a motion container). Motion is inherited from the parent's
// reduced-motion gating via variants.
export function KpiCard({ label, value, tone = "neutral", countTo, format }: Props) {
  const reduce = useReducedMotion();
  const toneClass =
    tone === "up"
      ? "text-up"
      : tone === "down"
        ? "text-down"
        : "text-content dark:text-content-dark";
  return (
    <motion.div
      variants={riseItem}
      whileHover={reduce ? undefined : { y: -1 }}
      className="rounded-xl border border-edge bg-surface-alt px-4 py-3 shadow-card transition-shadow hover:shadow-card-hover dark:border-edge-dark dark:bg-surface-dark-alt dark:shadow-none"
    >
      <div className="text-xs text-content-muted dark:text-content-dark-muted">
        {label}
      </div>
      <div className={`mt-1 text-lg font-semibold tabular-nums ${toneClass}`}>
        {countTo != null && format ? (
          <CountUp value={countTo} format={format} />
        ) : (
          value
        )}
      </div>
    </motion.div>
  );
}
