"use client";

import type { DashboardData } from "@/types";
import { StatCard, Badge } from "@/components/ui";
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
        <div className="kpi-grid">
            {kpis.map((k) => {
                const up = k.delta >= 0;
                return (
                    <Card key={k.label} decoration="top" decorationColor={up ? "kpi-up" : "kpi-down"}>
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-muted-foreground">{k.label}</span>
                            <Icon name={KPI_ICONS[k.label] ?? "dashboard"} size={22} className="text-muted-foreground" />
                        </div>
                        <div className="mt-4 flex items-baseline gap-2">
                            <span className="text-3xl font-bold">{k.value}</span>
                            <Badge tone={up ? "green" : "red"} className="text-xs font-medium">
                                {up ? "▲" : "▼"} {Math.abs(k.delta).toFixed(1)}%
                            </Badge>
                        </div>
                    </Card>
                );
            })}
        </div>
    );
}
