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
        <Card title="Quick Actions" className="bento-span-2 bento-card glass-card">
            <div className="mt-2 grid grid-cols-1 gap-4 sm:grid-cols-3">
                {ACTIONS.map((a, idx) => (
                    <Link
                        key={a.label}
                        href={a.href}
                        className={`stagger-${Math.min(idx + 1, 5)} group flex flex-col items-center justify-center rounded-xl border border-transparent bg-[var(--accent-surface)] p-4 transition-all duration-300 hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)] hover:shadow-lg`}
                    >
                        <span className="mb-3 rounded-full bg-[var(--background)] p-3 transition-colors group-hover:bg-white/20">
                            <Icon
                                name={a.icon}
                                size={24}
                                className="text-[var(--primary)] group-hover:text-current"
                            />
                        </span>
                        <span className="text-center text-sm font-medium">{a.label}</span>
                    </Link>
                ))}
            </div>
        </Card>
    );
}
