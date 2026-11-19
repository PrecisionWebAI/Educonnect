import type { LessonPlanContent, LessonPlanWeek } from "@/types";

/**
 * The Lesson Plan popup's rules, kept pure so `node --test` can cover them.
 *
 * The backend is still the authority on who may submit; these functions only decide what
 * the form shows and whether the button is worth pressing.
 */

export type PlanTone = "green" | "amber" | "red" | "muted";

/** `1 Nov - 7 Nov` - the line above the form. */
export function weekRangeLabel(week: LessonPlanWeek): string {
    return `${shortDate(week.startDate)} - ${shortDate(week.endDate)}`;
}

/** `6 teaching days`, or the honest holiday warning. */
export function teachingDaysLabel(week: LessonPlanWeek): string {
    const count = week.teachingDays.length;
    if (count === 0) return "No teaching days (holiday week)";
    return `${count} teaching day${count === 1 ? "" : "s"}`;
}

/** The status badge; no row is "Not submitted", not "Pending approval". */
export function planStatus(week: LessonPlanWeek): { label: string; tone: PlanTone } {
    if (week.status === "Approved") return { label: "Approved", tone: "green" };
    if (week.status === "Rejected") return { label: "Rejected", tone: "red" };
    if (week.status === "Submitted") return { label: "Submitted", tone: "amber" };
    return { label: "Not submitted", tone: "muted" };
}

/** The first required field that is still blank, or `null`. */
export function missingRequired(content: LessonPlanContent): string | null {
    if (!content.topics.trim()) return "Topics is required.";
    if (!content.learningObjectives.trim()) return "Learning objectives is required.";
    return null;
}

/** A rejection needs words; the server enforces the same rule (`422`). */
export function canReject(reason: string): boolean {
    return reason.trim().length > 0 && reason.trim().length <= 1000;
}

/** `3 submitted · 2 approved` for the Course row / review header. */
export function countsLabel(submitted: number, approved: number): string {
    if (submitted === 0) return "No plan";
    return `${submitted} submitted · ${approved} approved`;
}

/** Can this form be submitted? An approved week needs the change intent first. */
export function canSubmitWeek(
    week: LessonPlanWeek,
    content: LessonPlanContent,
    changeMode: boolean,
): boolean {
    if (missingRequired(content) !== null) return false;
    if (week.canEdit) return true;
    return week.status === "Approved" && week.canRequestChange && changeMode;
}

/** The six editable fields of a week, copied out for the form state. */
export function planContent(week: LessonPlanWeek): LessonPlanContent {
    return {
        topics: week.topics,
        learningObjectives: week.learningObjectives,
        activities: week.activities,
        homework: week.homework,
        resources: week.resources,
        assessment: week.assessment,
    };
}

/** `Nov 2026` for the month heading. */
export function monthLabel(year: number, month: number): string {
    const date = new Date(Date.UTC(year, month - 1, 1));
    return date.toLocaleDateString("en-GB", {
        month: "short",
        year: "numeric",
        timeZone: "UTC",
    });
}

function shortDate(value: string): string {
    const [, month, day] = value.split("-");
    const months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ];
    if (!month || !day) return value;
    return `${Number(day)} ${months[Number(month) - 1] ?? month}`;
}
