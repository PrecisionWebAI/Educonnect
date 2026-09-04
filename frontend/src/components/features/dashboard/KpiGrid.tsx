"use client";

import type { DashboardData } from "@/types";
import { StatCard } from "@/components/ui";
import Icon, { type IconName } from "@/components/ui/Icon";

// Row of headline KPI stat cards — no emoji; icon tiles like the stitch design.

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
            {kpis.map((k) => (
                <StatCard
                    key={k.label}
                    icon={<Icon name={KPI_ICONS[k.label] ?? "dashboard"} size={22} />}
                    label={k.label}
                    value={k.value}
                    delta={k.delta}
                />
            ))}
        </div>
    );
}
