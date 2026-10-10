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
            className="bento-span-2 bento-card glass-card grad-border"
            action={<Badge tone="amber" className="animate-pulse shadow-[0_0_10px_var(--chart-5)]">3 new</Badge>}
        >
            <ul className="space-y-3 mt-2">
                {INSIGHTS.map((i, idx) => (
                    <li key={i.text} className={`stagger-${Math.min(idx + 1, 5)} group flex items-start gap-3 p-3 rounded-lg bg-[var(--accent-surface)]/50 hover:bg-[var(--accent-surface)] transition-colors border border-[var(--border-subtle)] hover:border-[var(--primary)]`}>
                        <span className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--background)] group-hover:bg-white/20 transition-colors shrink-0">
                            <Icon name={i.icon} size={16} className={i.icon === "warning" ? "text-red-500" : "text-[var(--primary)]"} />
                        </span>
                        <span className="text-sm font-medium text-[var(--foreground)] mt-1 leading-snug">
                            {i.text}
                        </span>
                    </li>
                ))}
            </ul>
        </Card>
    );
}
