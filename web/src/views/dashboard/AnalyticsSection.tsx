import type { DrawdownPoint, RollingPoint } from "../../api/types";
import { DrawdownChart } from "../../charts/DrawdownChart";
import { RollingChart } from "../../charts/RollingChart";
import { Card, SectionHeader } from "../../components/Card";
import { ChartSkeleton } from "../../components/Skeleton";

interface Props {
  loading: boolean;
  drawdown?: DrawdownPoint[];
  rolling?: RollingPoint[];
}

// The "Analytics" block shown when include_analytics is on: an underwater
// (drawdown) chart + a rolling 1-yr return/vol chart. Skeletons while loading.
export function AnalyticsSection({ loading, drawdown, rolling }: Props) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card className="p-4">
        <SectionHeader>Underwater (drawdown from peak)</SectionHeader>
        {loading ? (
          <ChartSkeleton height={220} />
        ) : drawdown && drawdown.length > 0 ? (
          <DrawdownChart points={drawdown} />
        ) : (
          <EmptyNote>No drawdown data for this range.</EmptyNote>
        )}
      </Card>

      <Card className="p-4">
        <SectionHeader>Rolling 1-year return &amp; volatility</SectionHeader>
        {loading ? (
          <ChartSkeleton height={220} />
        ) : rolling && rolling.length > 0 ? (
          <RollingChart points={rolling} />
        ) : (
          <EmptyNote>
            Not enough history for a rolling 1-year window in this range.
          </EmptyNote>
        )}
      </Card>
    </div>
  );
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-[220px] items-center justify-center text-sm text-content-muted dark:text-content-dark-muted">
      {children}
    </div>
  );
}
