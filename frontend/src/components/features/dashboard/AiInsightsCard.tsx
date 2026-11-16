"use client";

import { Badge, Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";

// Stitch: admin_dashboard_desktop → AI insights / alerts card
const INSIGHTS: { icon: "warning" | "ai" | "trending"; text: string }[] = [
    { icon: "warning", text: "Class 9-B attendance dipped below 85% this week." },
    { icon: "ai", text: "AI suggests auto-reminder to 14 guardians of repeat absentees." },
    {
        icon: "trending",
        text: "Term-1 fee collection is ahead of target by 12% — lock budget early.",
    },
];

export default function AiInsightsCard() {
    return (
        <Card
            title="AI Insights"
            className="dashboard-card"
            action={<Badge tone="muted">3 new</Badge>}
        >
            <ul className="mt-2 space-y-3">
                {INSIGHTS.map((i) => (
                    <li
                        key={i.text}
                        className="border-border bg-background flex items-start gap-3 rounded-lg border p-3"
                    >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-surface)]">
                            <Icon
                                name={i.icon}
                                size={16}
                                className={
                                    i.icon === "warning"
                                        ? "text-amber-700 dark:text-amber-300"
                                        : "text-primary"
                                }
                            />
                        </span>
                        <span className="text-foreground text-sm leading-snug">{i.text}</span>
                    </li>
                ))}
            </ul>
        </Card>
    );
}
