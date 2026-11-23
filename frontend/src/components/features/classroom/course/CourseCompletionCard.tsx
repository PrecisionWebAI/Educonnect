"use client";

import { Card } from "@/components/ui";
import { completionDetail, completionWidth } from "@/lib/course/view";
import type { SectionCourse } from "@/types";

/**
 * The Course tab's top card: one number the whole section agrees on.
 *
 * D7: it is the **average of each subject's own percentage**, so a big subject cannot
 * outvote a small one. A section with no subjects, a section whose subjects have no
 * chapters and a plan at 0% are deliberately three different readings - an empty bar is
 * not "0% done".
 */
export default function CourseCompletionCard({ course }: { course: SectionCourse | undefined }) {
    if (!course) return null;

    const value = course.completionPercent;

    return (
        <Card title="Course completion">
            <div className="flex flex-col gap-2">
                <div className="flex flex-wrap items-baseline gap-2">
                    {value !== null && <span className="text-2xl font-semibold">{value}%</span>}
                    <span className="text-muted-foreground text-sm">
                        {completionDetail(course)}
                    </span>
                </div>
                <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                    <div
                        className="bg-primary h-full rounded-full transition-all"
                        style={{ width: completionWidth(course) }}
                    />
                </div>
            </div>
        </Card>
    );
}
