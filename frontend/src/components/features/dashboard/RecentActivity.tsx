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
            action={<Badge tone="green" className="animate-pulse shadow-[0_0_10px_var(--chart-4)]">Live</Badge>}
        >
            <ul className="space-y-4 mt-2">
                {ACTIVITY.map((a, idx) => (
                    <li key={a.text} className={`stagger-${Math.min(idx + 1, 5)} group flex items-start gap-4 p-3 rounded-lg hover:bg-[var(--accent-surface)] transition-colors border border-transparent hover:border-[var(--border-subtle)]`}>
                        <span className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] group-hover:bg-[var(--primary)] group-hover:text-[var(--primary-foreground)] transition-colors shrink-0">
                            <Icon name={a.icon} size={16} />
                        </span>
                        <div className="flex flex-col flex-1">
                            <span className="text-sm font-medium text-[var(--foreground)] leading-tight">{a.text}</span>
                            <span className="text-xs text-[var(--muted-foreground)] mt-1">{a.time}</span>
                        </div>
                    </li>
                ))}
            </ul>
        </Card>
    );
}
