"use client";

import type { DashboardData } from "@/types";
import { Badge } from "@/components/ui";
import Icon, { type IconName } from "@/components/ui/Icon";

import { Card } from "@/components/tremor/Card";

// Row of headline KPI stat cards using Tremor Card.

const KPI_ICONS: Record<string, IconName> = {
    "Total Students": "groups",
    "Attendance Today": "attendance",
    "Avg. Marks (Term 1)": "trending",
    "Fees Collected": "wallet",
    "Pending Approvals": "edit",
    "Open Tickets": "warning",
};

export default function KpiGrid({ kpis }: { kpis: DashboardData["kpis"] }) {
    return (
        <div className="bento-span-4 grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 lg:grid-cols-4">
            {kpis.map((k, idx) => {
                const up = k.delta >= 0;
                const staggerClass = `stagger-${Math.min(idx + 1, 5)}`;

                // Define colors based on trend
                const glowColor = up ? "var(--chart-4)" : "var(--destructive)";
                const iconBg = up
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                    : "bg-red-500/10 text-red-600 dark:text-red-400";

                return (
                    <Card
                        key={k.label}
                        className={`${staggerClass} group relative overflow-hidden`}
                    >
                        {/* Soft glowing background blob */}
                        <div
                            className="pointer-events-none absolute -top-10 -right-10 h-32 w-32 rounded-full opacity-20 blur-[40px] transition-opacity duration-500 group-hover:opacity-40"
                            style={{ backgroundColor: glowColor }}
                        />

                        <div className="relative z-10 flex h-full flex-col justify-between">
                            <div className="flex items-start justify-between">
                                <span className="text-sm font-medium tracking-wider text-[var(--muted-foreground)] uppercase">
                                    {k.label}
                                </span>
                                <div
                                    className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg} shadow-sm backdrop-blur-md`}
                                >
                                    <Icon name={KPI_ICONS[k.label] ?? "dashboard"} size={20} />
                                </div>
                            </div>

                            <div className="mt-6 flex items-end justify-between">
                                <span className="text-4xl font-bold tracking-tight text-[var(--foreground)] drop-shadow-sm">
                                    {k.value}
                                </span>
                                <Badge
                                    tone={up ? "green" : "red"}
                                    className="mb-1 px-2 py-1 text-xs font-semibold shadow-sm"
                                >
                                    {up ? "▲" : "▼"} {Math.abs(k.delta).toFixed(1)}%
                                </Badge>
                            </div>
                        </div>
                    </Card>
                );
            })}
        </div>
    );
}
