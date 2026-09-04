"use client";

import Link from "next/link";
import { Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";

// Stitch: admin_dashboard_desktop → "Quick Actions" grid
const ACTIONS = [
    { icon: "attendance" as const, label: "Mark attendance", href: "/dashboard/attendance" },
    { icon: "wallet" as const, label: "Collect fees", href: "/dashboard/finance" },
    { icon: "students" as const, label: "Issue ID cards", href: "/dashboard/students" },
];

export default function QuickActions() {
    return (
        <Card title="Quick Actions" className="dash-col-2">
            <div className="qa-grid">
                {ACTIONS.map((a) => (
                    <Link key={a.label} href={a.href} className="qa-tile">
                        <span className="qa-ico">
                            <Icon name={a.icon} size={20} />
                        </span>
                        <span>{a.label}</span>
                    </Link>
                ))}
            </div>
        </Card>
    );
}
