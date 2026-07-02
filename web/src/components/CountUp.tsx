import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";

interface Props {
  // The target numeric value to count toward.
  value: number;
  // Formats the (interpolated) number into the display string, e.g. formatCurrency.
  format: (n: number) => string;
  durationMs?: number;
}

// Animated count-up for numeric KPI values (dollar tiles). Used only where we
// hold the raw number — preformatted TWR "%" strings are rendered verbatim, not
// through this. Respects `prefers-reduced-motion` by snapping to the value.
export function CountUp({ value, format, durationMs = 700 }: Props) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (reduce) {
      setDisplay(value);
      return;
    }
    const from = fromRef.current;
    const to = value;
    if (from === to) return;
    const start = performance.now();

    function tick(now: number) {
      const t = Math.min(1, (now - start) / durationMs);
      // easeOutCubic for a natural settle.
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(from + (to - from) * eased);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = to;
      }
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      fromRef.current = to;
    };
  }, [value, durationMs, reduce]);

  return <>{format(display)}</>;
}
