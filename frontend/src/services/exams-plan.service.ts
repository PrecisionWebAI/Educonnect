import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type { ExamBody, MarkEntryPayload } from "@/lib/exams/view";
import type {
    ExamPaperGroup,
    ExamPaperPlan,
    ExamPlan,
    ExamResults,
    MarksSaved,
    PaperMarkRow,
} from "@/types";

/**
 * The Exams tab (Phase 7's backend).
 *
 * Two different stacks live under `/exams`: the **question-paper** routes
 * (`/exams/papers/{id}/finalize`, `/job`, `/sources/…` - see
 * `exam-builder.service.ts`) and the **plan** routes added in Phase 7. The plan
 * paths deliberately avoid the paper stack's shape, and nothing here touches it:
 *
 * * `/exams` - plan an exam with its date sheet, and list the ones this caller sees;
 * * `/exams/{id}/papers` - one exam and every sitting in it;
 * * `/exams/papers/{id}/marks` - the sheet; `POST` saves a draft, `PATCH` on one
 *   child's row is the **audited** correction after publication;
 * * `/exams/papers/{id}/publish` - the moment a family may see the marks;
 * * `/exams/{id}/results` - totals, grades and ranks, narrowed to the caller.
 *
 * Reading needs `marks.read`, writing `marks.update`; the server narrows further
 * (a teacher acts only on a subject they hold, a family sees only its own child),
 * so a `canEdit` flag on a paper is the answer to show, not a guess to make here.
 */

/** A decimal as the API writes it (`Decimal` -> JSON string) and we read it back. */
export function toExamPlan(payload: unknown): ExamPlan {
    return toCamel<ExamPlan>(payload);
}

/** The exams this caller may see - a section's own, or the whole school's. */
export async function listExams(params: {
    classroomId?: string | null;
    classId?: string | null;
    status?: string | null;
}): Promise<ExamPlan[]> {
    const query = new URLSearchParams();
    if (params.classroomId) query.set("classroom_id", params.classroomId);
    if (params.classId) query.set("class_id", params.classId);
    if (params.status) query.set("status", params.status);
    const suffix = query.toString();
    return toCamel<ExamPlan[]>(await api.get(`/exams${suffix ? `?${suffix}` : ""}`));
}

/** Plan an exam. A class exam needs its class-section; a school exam the office only. */
export async function createExam(body: ExamBody, status: "draft" | "scheduled" = "scheduled") {
    const payload = await api.post<unknown>("/exams", { ...body, status });
    return toExamPlan(payload);
}

/**
 * Change an exam.
 *
 * `papers` **replaces the whole date sheet** when it is sent, which is why the
 * form sends every row and not just the edited one. A published paper is never
 * silently re-cut: the server refuses (`409`) rather than moving a date behind a
 * family's back.
 */
export async function updateExam(
    examId: string,
    body: Partial<ExamBody> & { status?: string },
): Promise<ExamPlan> {
    const payload = await api.patch<unknown>(`/exams/${examId}`, body);
    return toExamPlan(payload);
}

/** One exam with its date sheet, each paper saying whether this caller may edit it. */
export async function getExam(examId: string): Promise<ExamPlan> {
    return toExamPlan(await api.get<unknown>(`/exams/${examId}/papers`));
}

/** The sheet for one paper: every child in its class, marked or not. */
export async function getPaperMarks(paperId: string): Promise<PaperMarkRow[]> {
    return toCamel<PaperMarkRow[]>(await api.get<unknown>(`/exams/papers/${paperId}/marks`));
}

/**
 * Save a draft of one paper's scores.
 *
 * Upsert per child, so pressing Save twice cannot double a score. Refused with
 * `409` once the paper is published - a published mark changes through
 * `changeMark`, and only with a reason on the record.
 */
export async function savePaperMarks(
    paperId: string,
    entries: MarkEntryPayload[],
): Promise<MarksSaved> {
    return toCamel<MarksSaved>(
        await api.post<unknown>(`/exams/papers/${paperId}/marks`, { entries }),
    );
}

/** Publish one sitting's marks - the moment families may see them. */
export async function publishPaper(paperId: string): Promise<ExamPaperPlan> {
    return toCamel<ExamPaperPlan>(await api.post<unknown>(`/exams/papers/${paperId}/publish`));
}

/**
 * Correct **one published** mark.
 *
 * The server writes `marks_audit` in the same transaction and tells the family,
 * so the reason is not decoration - it is the record of why the number moved.
 */
export async function changeMark(
    paperId: string,
    studentId: string,
    change: { marksObtained: number | null; absent?: boolean; reason?: string | null },
): Promise<PaperMarkRow> {
    const payload = await api.patch<unknown>(`/exams/papers/${paperId}/marks/${studentId}`, {
        marks_obtained: change.marksObtained,
        absent: change.absent,
        reason: change.reason ?? null,
    });
    return toCamel<PaperMarkRow>(payload);
}

/** Marks, grades and ranks - narrowed to the caller (a family sees its own child). */
export async function getExamResults(examId: string): Promise<ExamResults> {
    return toCamel<ExamResults>(await api.get<unknown>(`/exams/${examId}/results`));
}

/**
 * Edit what every section of a shared paper has in common - its title, chapters (by
 * name) and maximum. Refused with `409` once any section has marks or is published:
 * the question paper has been sat. Detach a section to give it a paper of its own.
 */
export async function updatePaperGroup(
    groupId: string,
    changes: {
        displayTitle?: string | null;
        chapters?: string[];
        maxMarks?: number;
        passingMarks?: number;
    },
): Promise<ExamPaperGroup> {
    const body: Record<string, unknown> = {};
    if (changes.displayTitle !== undefined) body.display_title = changes.displayTitle;
    if (changes.chapters !== undefined) body.chapters = changes.chapters;
    if (changes.maxMarks !== undefined) body.max_marks = changes.maxMarks;
    if (changes.passingMarks !== undefined) body.passing_marks = changes.passingMarks;
    return toCamel<ExamPaperGroup>(
        await api.patch<unknown>(`/exams/paper-groups/${groupId}`, body),
    );
}

/**
 * Give one section its own paper, leaving the group for everyone else. The group's
 * chapters are matched to the section's own by name; a name it lacks is a `409` that
 * lists it. Allowed even when the shared paper is locked.
 */
export async function detachPaper(groupId: string, paperId: string): Promise<ExamPaperPlan> {
    return toCamel<ExamPaperPlan>(
        await api.post<unknown>(`/exams/paper-groups/${groupId}/papers/${paperId}/detach`),
    );
}
