"use client";

import { Badge, Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";

// Stitch: admin_dashboard_desktop → "Recent Activity" feed
const ACTIVITY: { icon: "check" | "ai" | "wallet" | "edit"; text: string; time: string }[] = [
    { icon: "check", text: "Attendance synced · Class 10-A", time: "8 min ago" },
    { icon: "ai", text: "Auto-verified by EduConnect AI · Fee receipt #1042", time: "22 min ago" },
    { icon: "wallet", text: "Bank reconciliation completed · ₹1.2L matched", time: "1 hr ago" },
    { icon: "edit", text: "Term-1 marks entry approved · Mathematics", time: "2 hrs ago" },
];

export default function RecentActivity() {
    return (
        <Card
            title="Recent Activity"
            className="bento-span-2 bento-card glass-card"
            action={
                <Badge tone="green" className="animate-pulse shadow-[0_0_10px_var(--chart-4)]">
                    Live
                </Badge>
            }
        >
            <ul className="mt-2 space-y-4">
                {ACTIVITY.map((a, idx) => (
                    <li
                        key={a.text}
                        className={`stagger-${Math.min(idx + 1, 5)} group flex items-start gap-4 rounded-lg border border-transparent p-3 transition-colors hover:border-[var(--border-subtle)] hover:bg-[var(--accent-surface)]`}
                    >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--primary)]/10 text-[var(--primary)] transition-colors group-hover:bg-[var(--primary)] group-hover:text-[var(--primary-foreground)]">
                            <Icon name={a.icon} size={16} />
                        </span>
                        <div className="flex flex-1 flex-col">
                            <span className="text-sm leading-tight font-medium text-[var(--foreground)]">
                                {a.text}
                            </span>
                            <span className="mt-1 text-xs text-[var(--muted-foreground)]">
                                {a.time}
                            </span>
                        </div>
                    </li>
                ))}
            </ul>
        </Card>
    );
}
