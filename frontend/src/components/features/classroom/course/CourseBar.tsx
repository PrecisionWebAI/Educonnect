"use client";

import type { BarSegment } from "@/lib/course/view";
import { barSegments, chaptersLabel } from "@/lib/course/view";
import type { CourseSubject } from "@/types";
import { cn } from "cn";

// The segmented bar: one colour per teacher who finished chapters, then the grey
// "not done" remainder - with a legend that names each slice.
//
// Why a bar and not a percentage: the point of the Course tab is **who** got the class
// through the book. A subject that changed teacher halfway shows two colours, and the
// legend says "ansari 2/10 · bose 1/10", which no single number can.

const TONE_CLASS: Record<BarSegment["tone"], string> = {
    violet: "bg-violet-400",
    sky: "bg-sky-400",
    amber: "bg-amber-400",
    emerald: "bg-emerald-400",
    rose: "bg-rose-400",
    slate: "bg-slate-200",
};

export default function CourseBar({ subject }: { subject: CourseSubject }) {
    const segments = barSegments(subject);

    if (segments.length === 0) {
        return (
            <p style={{ color: "var(--muted)", fontSize: "0.82rem" }}>No chapters planned yet</p>
        );
    }

    return (
        <div className="flex flex-col gap-2">
            <div
                className="flex h-3 w-full overflow-hidden rounded-full"
                role="img"
                aria-label={`${subject.done} of ${subject.total} chapters done`}
            >
                {segments.map((segment) => (
                    <span
                        key={segment.key}
                        className={cn("h-full", TONE_CLASS[segment.tone])}
                        style={{ width: `${segment.share}%` }}
                        title={`${segment.label} · ${chaptersLabel(
                            segment.chapters,
                            subject.total,
                        )} (${segment.share}%)`}
                    />
                ))}
            </div>

            <ul className="flex flex-wrap gap-x-4 gap-y-1">
                {segments.map((segment) => (
                    <li
                        key={segment.key}
                        className="flex items-center gap-1.5"
                        style={{ fontSize: "0.76rem" }}
                    >
                        <span
                            className={cn(
                                "inline-block h-2 w-2 rounded-full",
                                TONE_CLASS[segment.tone],
                            )}
                        />
                        <span>{segment.label}</span>
                        <span style={{ color: "var(--muted)" }}>
                            {chaptersLabel(segment.chapters, subject.total)}
                        </span>
                    </li>
                ))}
            </ul>
        </div>
    );
}
