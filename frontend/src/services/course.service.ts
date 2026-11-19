import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    BulkReviewResult,
    CourseChapter,
    CourseSubjectRow,
    CourseSummary,
    CourseTeacher,
    CourseTeacherAssignment,
    CourseTeacherRow,
    LessonPlanContent,
    LessonPlanWeek,
    ReviewDecision,
    ReviewRow,
    SectionCourse,
    SubjectRow,
    TeacherCourseDetail,
} from "@/types";

/**
 * The Course tab.
 *
 * One read for the whole tab - the section's subjects, who teaches them, each person's
 * share and this section's progress - so the screen never assembles the bar from several
 * calls that could disagree. The number it shows (`percent`) is the server's, not a
 * division done in the browser.
 *
 * `includeArchived` is the "Show archived" switch; the office uses it to restore a
 * subject it retired by mistake.
 */
export async function getSectionCourse(
    sectionId: string,
    includeArchived = false,
): Promise<SectionCourse> {
    const query = includeArchived ? "?include_archived=true" : "";
    const payload = await api.get<unknown>(`/classroom/sections/${sectionId}/course${query}`);
    return toCamel<SectionCourse>(payload);
}

/** The master subjects this section can still add (the Add Subject dropdown). */
export async function getAvailableSubjects(sectionId: string): Promise<SubjectRow[]> {
    const payload = await api.get<unknown>(`/classroom/sections/${sectionId}/available-subjects`);
    return toCamel<SubjectRow[]>(payload);
}

/**
 * Add a subject to this section.
 *
 * Exactly one of `subjectId` (a master subject) and `name` (the Custom subject) is sent.
 * The row exists before a teacher does - assigning one is the next step.
 */
export async function addSectionSubject(
    sectionId: string,
    input: { subjectId?: string; name?: string },
): Promise<CourseSubjectRow> {
    const payload = await api.post<unknown>(`/classroom/sections/${sectionId}/subjects`, {
        subject_id: input.subjectId,
        name: input.name,
    });
    return toCamel<CourseSubjectRow>(payload);
}

/** Retire a section subject; its plans, chapters and history stay. */
export async function archiveCourseSubject(classroomSubjectId: string): Promise<CourseSubjectRow> {
    const payload = await api.patch<unknown>(`/course/subjects/${classroomSubjectId}/archive`);
    return toCamel<CourseSubjectRow>(payload);
}

/** Bring an archived section subject back (the master must still be active). */
export async function restoreCourseSubject(classroomSubjectId: string): Promise<CourseSubjectRow> {
    const payload = await api.patch<unknown>(`/course/subjects/${classroomSubjectId}/restore`);
    return toCamel<CourseSubjectRow>(payload);
}

/**
 * Delete an empty section subject. The server refuses one with a lesson plan or a
 * completed chapter (`409`) and says to archive it instead.
 */
export async function deleteCourseSubject(classroomSubjectId: string): Promise<void> {
    await api.delete<unknown>(`/course/subjects/${classroomSubjectId}`);
}

/**
 * Assign or change the teacher of one section subject.
 *
 * The server closes the open row the day before `effectiveFrom` and opens a new one, so
 * the timeline is history rather than an overwrite. The answer may carry a `warning`
 * (the school's workload rule says this teacher is already full) - the assignment has
 * still been saved, and the caller shows the sentence without pretending it failed.
 */
export async function assignCourseTeacher(
    classroomSubjectId: string,
    input: { teacherId: string; effectiveFrom?: string | null },
): Promise<CourseTeacherAssignment> {
    const payload = await api.put<unknown>(`/course/subjects/${classroomSubjectId}/teacher`, {
        teacher_id: input.teacherId,
        effective_from: input.effectiveFrom ?? null,
    });
    return toCamel<CourseTeacherAssignment>(payload);
}

/** Everyone who held this section subject, oldest first, with their own chapter credit. */
export async function getCourseTeacherHistory(
    classroomSubjectId: string,
): Promise<CourseTeacher[]> {
    const payload = await api.get<unknown>(`/course/subjects/${classroomSubjectId}/teachers`);
    return toCamel<CourseTeacher[]>(payload);
}

/** The class's chapter plan for one section subject, with this section's progress. */
export async function getChapters(classroomSubjectId: string): Promise<CourseChapter[]> {
    const payload = await api.get<unknown>(`/course/subjects/${classroomSubjectId}/chapters`);
    return toCamel<CourseChapter[]>(payload);
}

/** Add a chapter to the class plan (the office only). */
export async function createChapter(
    classroomSubjectId: string,
    input: { name: string; plannedDate?: string | null },
): Promise<CourseChapter> {
    const payload = await api.post<unknown>(`/course/subjects/${classroomSubjectId}/chapters`, {
        name: input.name,
        planned_date: input.plannedDate ?? null,
    });
    return toCamel<CourseChapter>(payload);
}

/**
 * Rename, re-date or move one chapter.
 *
 * `sequence` is a **position**, not a stored number: the server renumbers the list, so a
 * move can never leave two chapters at position 2. `plannedDate: null` clears the date;
 * omitting it leaves the date alone.
 */
export async function updateChapter(
    chapterId: string,
    input: { name?: string; sequence?: number; plannedDate?: string | null },
): Promise<CourseChapter> {
    const payload = await api.patch<unknown>(`/course/chapters/${chapterId}`, {
        name: input.name,
        sequence: input.sequence,
        planned_date: input.plannedDate,
    });
    return toCamel<CourseChapter>(payload);
}

/** Delete an unstarted chapter; a completed tick or an exam paper blocks it (`409`). */
export async function deleteChapter(chapterId: string): Promise<void> {
    await api.delete<unknown>(`/course/chapters/${chapterId}`);
}

/** The month's Week 1-5 tabs, with this subject's plan and progress. */
export async function getLessonPlanMonth(
    classroomSubjectId: string,
    year: number,
    month: number,
): Promise<LessonPlanWeek[]> {
    const payload = await api.get<unknown>(
        `/course/subjects/${classroomSubjectId}/lesson-plans?year=${year}&month=${month}`,
    );
    return toCamel<LessonPlanWeek[]>(payload);
}

/**
 * Submit one week. There is no draft: this writes the working row **and** its history
 * snapshot. `expectedVersion` makes a stale tab a `409` instead of an overwrite; an
 * approved week needs `intent: "change"`.
 */
export async function submitLessonPlanWeek(
    classroomSubjectId: string,
    year: number,
    month: number,
    weekNo: number,
    input: LessonPlanContent & {
        expectedVersion: number;
        intent?: "change" | null;
    },
): Promise<LessonPlanWeek> {
    const payload = await api.put<unknown>(
        `/course/subjects/${classroomSubjectId}/lesson-plans/${year}/${month}/${weekNo}`,
        {
            topics: input.topics,
            learning_objectives: input.learningObjectives,
            activities: input.activities,
            homework: input.homework,
            resources: input.resources,
            assessment: input.assessment,
            expected_version: input.expectedVersion,
            intent: input.intent ?? null,
        },
    );
    return toCamel<LessonPlanWeek>(payload);
}

/** Submitted weeks waiting for the principal, oldest first. */
export async function getReviewQueue(params?: {
    sectionId?: string | null;
    skip?: number;
    limit?: number;
}): Promise<ReviewRow[]> {
    const query = new URLSearchParams();
    if (params?.sectionId) query.set("section_id", params.sectionId);
    if (params?.skip) query.set("skip", String(params.skip));
    if (params?.limit) query.set("limit", String(params.limit));
    const suffix = query.toString() ? `?${query.toString()}` : "";
    const payload = await api.get<unknown>(`/course/reviews${suffix}`);
    return toCamel<ReviewRow[]>(payload);
}

/** The pending-approval badge count. */
export async function getReviewCount(sectionId?: string | null): Promise<number> {
    const suffix = sectionId ? `?section_id=${sectionId}` : "";
    const payload = await api.get<unknown>(`/course/reviews/count${suffix}`);
    return toCamel<{ count: number }>(payload).count;
}

/** Approve the version the reviewer saw; repeating it is a safe `200`. */
export async function approveLessonPlan(
    planId: string,
    expectedVersion: number,
): Promise<ReviewDecision> {
    const payload = await api.post<unknown>(`/course/lesson-plans/${planId}/approve`, {
        expected_version: expectedVersion,
    });
    return toCamel<ReviewDecision>(payload);
}

/** Reject a submitted week; the reason is mandatory. */
export async function rejectLessonPlan(
    planId: string,
    reason: string,
    expectedVersion: number,
): Promise<ReviewDecision> {
    const payload = await api.post<unknown>(`/course/lesson-plans/${planId}/reject`, {
        reason,
        expected_version: expectedVersion,
    });
    return toCamel<ReviewDecision>(payload);
}

/** Approve the reviewed rows; stale ones come back in `skipped`. */
export async function approveManyLessonPlans(
    items: { planId: string; expectedVersion: number }[],
): Promise<BulkReviewResult> {
    const payload = await api.post<unknown>("/course/lesson-plans/approve-many", {
        items: items.map((item) => ({
            plan_id: item.planId,
            expected_version: item.expectedVersion,
        })),
    });
    return toCamel<BulkReviewResult>(payload);
}

/** The Course badge: scoped subjects, submitted weeks and D7 completion. */
export async function getCourseSummary(): Promise<CourseSummary> {
    const payload = await api.get<unknown>("/course/summary");
    return toCamel<CourseSummary>(payload);
}

/** Teachers > Course: the roll with pending/behind/completion counts. */
export async function getCourseTeachers(params?: {
    q?: string;
    skip?: number;
    limit?: number;
}): Promise<CourseTeacherRow[]> {
    const query = new URLSearchParams();
    if (params?.q) query.set("q", params.q);
    if (params?.skip) query.set("skip", String(params.skip));
    if (params?.limit) query.set("limit", String(params.limit));
    const suffix = query.toString() ? `?${query.toString()}` : "";
    const payload = await api.get<unknown>(`/course/teachers${suffix}`);
    return toCamel<CourseTeacherRow[]>(payload);
}

/** One teacher's subjects/sections, month weeks and chapter progress. */
export async function getTeacherCourse(employeeId: string): Promise<TeacherCourseDetail> {
    const payload = await api.get<unknown>(`/course/teachers/${employeeId}`);
    return toCamel<TeacherCourseDetail>(payload);
}

/** The signed-in teacher's own course - no id from the browser. */
export async function getMyCourse(): Promise<TeacherCourseDetail> {
    const payload = await api.get<unknown>("/course/my");
    return toCamel<TeacherCourseDetail>(payload);
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
