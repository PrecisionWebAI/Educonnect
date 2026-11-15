import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type { CourseChapter, SectionCourse } from "@/types";

/**
 * The Course tab (Phase 5's backend).
 *
 * One read for the whole tab - the plan, who teaches it, each person's share and this
 * section's progress - so the screen never assembles the bar from several calls that
 * could disagree. The number it shows (`percent`) is the server's, not a division done
 * in the browser.
 */
export async function getSectionCourse(sectionId: string): Promise<SectionCourse> {
    const payload = await api.get<unknown>(`/classroom/sections/${sectionId}/course`);
    return toCamel<SectionCourse>(payload);
}

/** The words a tick accepts - the tab's own stepper. */
export type ChapterTick = CourseChapter["status"];

/**
 * Move one chapter for one class-section.
 *
 * The section is in the body because a chapter belongs to the **class**: the same
 * chapter can be done in 9-A and not in 9-B. The server refuses a caller who neither
 * holds the subject now nor holds the office's `classes.update` (`403`) - the button
 * being hidden is a courtesy, this call is the rule.
 */
export async function tickChapter(
    chapterId: string,
    classroomId: string,
    status: ChapterTick,
): Promise<CourseChapter> {
    const payload = await api.patch<unknown>(`/course/chapters/${chapterId}/progress`, {
        classroom_id: classroomId,
        status,
    });
    return toCamel<CourseChapter>(payload);
}
