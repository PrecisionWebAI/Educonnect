"use client";

import { Badge, Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";

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
            className="dashboard-card xl:col-span-4"
            action={<Badge tone="muted">Live</Badge>}
        >
            <ul className="mt-2 space-y-1">
                {ACTIVITY.map((a) => (
                    <li key={a.text} className="flex items-start gap-3 rounded-lg px-2 py-3">
                        <span className="text-primary flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-surface)]">
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
