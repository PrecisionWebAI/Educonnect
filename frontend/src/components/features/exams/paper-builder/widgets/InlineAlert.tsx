"use client";

// ============================================================
// InlineAlert — the professional failure notice for the paper builder.
//
// The teacher must never read raw API text. `describeError()` in the service
// layer turns a failure into a title + one plain sentence ("Access denied" /
// "This question is locked. Unlock it first..."), and this renders that as a
// calm card with an optional action — usually the Unlock button, so the way
// forward is right next to the message.
// ============================================================

import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { Button } from "@/components/ui";

export type AlertTone = "error" | "warning" | "info" | "success";

const TONE_STYLES: Record<
    AlertTone,
    { wrap: string; icon: string; Icon: typeof Info }
> = {
    error: {
        wrap: "border-red-300/70 bg-red-50 dark:border-red-400/30 dark:bg-red-500/10",
        icon: "text-red-600 dark:text-red-300",
        Icon: AlertTriangle,
    },
    warning: {
        wrap: "border-amber-300/70 bg-amber-50 dark:border-amber-400/30 dark:bg-amber-500/10",
        icon: "text-amber-600 dark:text-amber-300",
        Icon: AlertTriangle,
    },
    info: {
        wrap: "border-violet-300/70 bg-violet-50 dark:border-violet-400/30 dark:bg-violet-500/10",
        icon: "text-violet-600 dark:text-violet-300",
        Icon: Info,
    },
    success: {
        wrap: "border-emerald-300/70 bg-emerald-50 dark:border-emerald-400/30 dark:bg-emerald-500/10",
        icon: "text-emerald-600 dark:text-emerald-300",
        Icon: CheckCircle2,
    },
};

export default function InlineAlert({
    tone = "error",
    title,
    message,
    actionLabel,
    onAction,
    onDismiss,
}: {
    tone?: AlertTone;
    title: string;
    message: string;
    /** Optional next step, e.g. "Unlock" — rendered inside the alert. */
    actionLabel?: string;
    onAction?: () => void;
    onDismiss?: () => void;
}) {
    const style = TONE_STYLES[tone];
    const Icon = style.Icon;

    return (
        <div
            role="alert"
            className={`flex items-start gap-3 rounded-md border p-3 ${style.wrap}`}
        >
            <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${style.icon}`} />
            <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{title}</p>
                <p className="text-muted-foreground mt-0.5 text-sm">{message}</p>
            </div>
            {actionLabel && onAction && (
                <Button variant="outline" size="sm" onClick={onAction}>
                    {actionLabel}
                </Button>
            )}
            {onDismiss && (
                <button
                    type="button"
                    onClick={onDismiss}
                    aria-label="Dismiss"
                    className="text-muted-foreground hover:text-foreground transition-colors"
                >
                    <X className="h-4 w-4" />
                </button>
            )}
        </div>
    );
}
