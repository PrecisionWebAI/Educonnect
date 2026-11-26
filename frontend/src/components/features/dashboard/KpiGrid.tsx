"use client";

import type { DashboardData } from "@/types";
import { Badge } from "@/components/ui";
import Icon, { type IconName } from "@/components/ui/Icon";

import { Card } from "@/components/tremor/Card";

// The four headline metrics stay prominent; secondary metrics remain easy to scan.

const KPI_ICONS: Record<string, IconName> = {
    "Total Students": "groups",
    "Attendance Today": "attendance",
    "Avg. Marks (Term 1)": "trending",
    "Fees Collected": "wallet",
    "Pending Approvals": "edit",
    "Open Tickets": "warning",
};

const KPI_ACCENTS: Record<string, string> = {
    "Total Students": "dashboard-kpi--teal",
    "Attendance Today": "dashboard-kpi--mint",
    "Fees Collected": "dashboard-kpi--amber",
    "Avg. Marks (Term 1)": "dashboard-kpi--forest",
};

export default function KpiGrid({ kpis }: { kpis: DashboardData["kpis"] }) {
    const priority = [
        "Total Students",
        "Attendance Today",
        "Fees Collected",
        "Avg. Marks (Term 1)",
    ];
    const ordered = [...kpis].sort((a, b) => {
        const aPriority = priority.indexOf(a.label);
        const bPriority = priority.indexOf(b.label);
        return (
            (aPriority < 0 ? priority.length : aPriority) -
            (bPriority < 0 ? priority.length : bPriority)
        );
    });
    const headlineKpis = ordered.slice(0, 4);
    const additionalKpis = ordered.slice(4);

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {headlineKpis.map((k) => (
                    <Card
                        key={k.label}
                        className={`dashboard-card dashboard-kpi ${KPI_ACCENTS[k.label] ?? "dashboard-kpi--teal"}`}
                    >
                        <div className="flex items-start justify-between gap-3">
                            <span className="text-muted-foreground text-sm font-medium">
                                {k.label}
                            </span>
                            <span className="dashboard-kpi-icon flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                                <Icon name={KPI_ICONS[k.label] ?? "dashboard"} size={18} />
                            </span>
                        </div>
                        <div className="mt-5 flex flex-wrap items-baseline justify-between gap-2">
                            <span className="text-foreground text-3xl font-semibold tracking-tight">
                                {k.value}
                            </span>
                            {k.delta !== 0 && (
                                <Badge tone="muted">
                                    {k.delta > 0 ? "+" : "-"}
                                    {Math.abs(k.delta).toFixed(1)}%
                                </Badge>
                            )}
                        </div>
                    </Card>
                ))}
            </div>

            {additionalKpis.length > 0 && (
                <section
                    aria-label="Needs attention"
                    className="dashboard-glass-surface grid grid-cols-1 gap-x-8 gap-y-3 rounded-xl border px-5 py-4 sm:grid-cols-[auto_1fr]"
                >
                    <h2 className="text-foreground text-sm font-semibold">Needs attention</h2>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        {additionalKpis.map((k) => (
                            <div
                                key={k.label}
                                className="flex items-center justify-between gap-3 text-sm"
                            >
                                <span className="text-muted-foreground">{k.label}</span>
                                <span className="flex items-center gap-2">
                                    <span className="text-foreground font-semibold">{k.value}</span>
                                    {k.delta !== 0 && (
                                        <span className="text-muted-foreground text-xs">
                                            {k.delta > 0 ? "+" : "-"}
                                            {Math.abs(k.delta).toFixed(1)}%
                                        </span>
                                    )}
                                </span>
                            </div>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}
