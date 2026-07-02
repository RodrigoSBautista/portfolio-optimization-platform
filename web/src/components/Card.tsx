import { motion } from "framer-motion";
import { riseItem } from "../lib/motion";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  // Render as a motion item (for staggered entrance inside a container).
  animate?: boolean;
  hover?: boolean;
}

// A surface card: subtle border + soft shadow, optional gentle hover lift, and
// optional entrance as a motion item. Dark theme leans on the border, light on
// the layered shadow.
export function Card({ children, className = "", animate = false, hover = false }: CardProps) {
  const base =
    "rounded-xl border border-edge bg-surface shadow-card dark:border-edge-dark dark:bg-surface-dark dark:shadow-none";
  const hoverCls = hover
    ? "transition-shadow hover:shadow-card-hover"
    : "";
  if (animate) {
    return (
      <motion.div
        variants={riseItem}
        whileHover={hover ? { y: -1 } : undefined}
        className={`${base} ${hoverCls} ${className}`}
      >
        {children}
      </motion.div>
    );
  }
  return <div className={`${base} ${hoverCls} ${className}`}>{children}</div>;
}

// A consistent section header used above tables/charts inside cards.
export function SectionHeader({ children }: { children: React.ReactNode }) {
  return <h2 className="mb-3 text-sm font-semibold">{children}</h2>;
}
