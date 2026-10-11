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
            action={
                <Badge tone="amber" className="animate-pulse shadow-[0_0_10px_var(--chart-5)]">
                    3 new
                </Badge>
            }
        >
            <ul className="mt-2 space-y-3">
                {INSIGHTS.map((i, idx) => (
                    <li
                        key={i.text}
                        className={`stagger-${Math.min(idx + 1, 5)} group flex items-start gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--accent-surface)]/50 p-3 transition-colors hover:border-[var(--primary)] hover:bg-[var(--accent-surface)]`}
                    >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--background)] transition-colors group-hover:bg-white/20">
                            <Icon
                                name={i.icon}
                                size={16}
                                className={
                                    i.icon === "warning" ? "text-red-500" : "text-[var(--primary)]"
                                }
                            />
                        </span>
                        <span className="mt-1 text-sm leading-snug font-medium text-[var(--foreground)]">
                            {i.text}
                        </span>
                    </li>
                ))}
            </ul>
        </Card>
    );
}
