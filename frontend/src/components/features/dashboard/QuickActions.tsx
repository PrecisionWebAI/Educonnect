"use client";

import Link from "next/link";
import { Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";

// The student directory and the attendance register now live **inside the
// Classroom** (open a class-section), so these two actions point there.
const ACTIONS = [
    { icon: "attendance" as const, label: "Mark attendance", href: "/dashboard/classroom" },
    { icon: "wallet" as const, label: "Collect fees", href: "/dashboard/finance" },
    { icon: "students" as const, label: "Students & classes", href: "/dashboard/classroom" },
];

export default function QuickActions() {
    return (
        <Card title="Quick actions" className="dashboard-card">
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3 xl:grid-cols-1">
                {ACTIONS.map((a) => (
                    <Link
                        key={a.label}
                        href={a.href}
                        className="group border-border bg-background hover:border-primary flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors hover:bg-[var(--accent-surface)]"
                    >
                        <span className="text-primary flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-surface)]">
                            <Icon name={a.icon} size={18} />
                        </span>
                        <span>{a.label}</span>
                    </Link>
                ))}
            </div>
        </Card>
    );
}
