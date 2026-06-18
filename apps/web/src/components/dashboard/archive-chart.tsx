"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useArchiveActivity } from "@/lib/queries";

const chartConfig = {
  tracks: { label: "Tracks", color: "var(--chart-2)" },
  stems: { label: "Stems", color: "var(--chart-1)" },
} satisfies ChartConfig;

export function ArchiveChart() {
  const { data: activity, error, refetch } = useArchiveActivity(7);

  const data = useMemo(
    () =>
      (activity ?? []).map((d) => ({
        date: new Date(d.date + "T00:00:00").toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        tracks: d.tracks,
        stems: d.stems,
      })),
    [activity],
  );

  const totalStems = data.reduce((sum, d) => sum + d.stems, 0);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Separation Activity</CardTitle>
        <CardDescription className="text-xs">
          Tracks ingested and stems produced · last 7 days
        </CardDescription>
        <CardAction className="text-right self-center">
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
            Stems
          </div>
          <div className="text-lg font-semibold tabular-nums tracking-tight leading-tight">
            {totalStems}
          </div>
        </CardAction>
      </CardHeader>
      <CardContent className="p-5">
        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No activity yet"
            description="Add tracks to see separation activity here."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <CartesianGrid
                vertical={false}
                strokeDasharray="3 3"
                stroke="var(--border)"
              />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tickMargin={10}
                fontSize={11}
              />
              <YAxis
                allowDecimals={false}
                tickLine={false}
                axisLine={false}
                tickMargin={6}
                fontSize={11}
                width={28}
              />
              <ChartTooltip
                cursor={{ fill: "var(--accent-subtle)" }}
                content={<ChartTooltipContent />}
              />
              <Bar
                dataKey="tracks"
                fill="var(--color-tracks)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
              <Bar
                dataKey="stems"
                fill="var(--color-stems)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
