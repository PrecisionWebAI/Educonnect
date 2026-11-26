import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type { ExamBody, MarkEntryPayload } from "@/lib/exams/view";
import type {
    ExamPaperGroup,
    ExamPaperPlan,
    ExamPlan,
    ExamResults,
    MarksSaved,
    MarkAudit,
    MarkingDefaults,
    PaperMarkRow,
    ResultOverview,
    Syllabus,
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

/**
 * What a new paper out of `total` marks starts from: 33% pass marks, the grade that
 * earns, the school's ladder, how results are shown. Starting values only - the form
 * lets the teacher change any of them for that one paper.
 */
export async function getMarkingDefaults(total: number): Promise<MarkingDefaults> {
    return toCamel<MarkingDefaults>(
        await api.get(`/exams/marking-defaults?total=${encodeURIComponent(String(total))}`),
    );
}

/** A class-section of the section's class that can be picked next to it. */
export interface SectionChoice {
    classroomId: string;
    label: string;
    /** The names of its active subjects. */
    subjects: string[];
}

/** The real class-sections of this section's class (the "Sections" pickers). */
export async function getSectionChoices(classroomId: string): Promise<SectionChoice[]> {
    return toCamel<SectionChoice[]>(
        await api.get(`/exams/sections?classroom_id=${encodeURIComponent(classroomId)}`),
    );
}

/** The body of `POST /exams/class-tests` (snake_case, as the API reads it). */
export type ClassTestBody = Record<string, unknown>;

/** Schedule a class test for one or several sections of one class. */
export async function createClassTest(body: ClassTestBody): Promise<ExamPlan> {
    return toExamPlan(await api.post("/exams/class-tests", body));
}

/** Edit a class test; only the fields sent change (a new date is a reschedule). */
export async function updateClassTest(examId: string, body: ClassTestBody): Promise<ExamPlan> {
    return toExamPlan(await api.patch(`/exams/class-tests/${examId}`, body));
}

/** Call a class test off: the record and any marks stay, the families are told. */
export async function cancelClassTest(examId: string): Promise<ExamPlan> {
    return toExamPlan(await api.post(`/exams/class-tests/${examId}/cancel`, {}));
}

/** Delete a class test nobody has marks for (`409` otherwise). */
export async function deleteClassTest(examId: string): Promise<void> {
    await api.delete<void>(`/exams/class-tests/${examId}`);
}

/**
 * Class Test **or** School Exam results for the year on screen.
 *
 * Staff pass the section (the class view: every test, class average / highest / lowest /
 * passed / failed, and each child's subject-wise and overall percentage). A student or
 * guardian passes none and gets only their own children, only published tests.
 */
export async function getResultOverview(
    kind: "class_test" | "school_exam",
    classroomId?: string | null,
): Promise<ResultOverview> {
    const query = new URLSearchParams({ kind });
    if (classroomId) query.set("classroom_id", classroomId);
    return toCamel<ResultOverview>(await api.get(`/exams/results/overview?${query}`));
}

/** Every correction made to a paper's published marks, newest first. */
export async function getMarkHistory(paperId: string): Promise<MarkAudit[]> {
    return toCamel<MarkAudit[]>(await api.get(`/exams/papers/${paperId}/marks/history`));
}

/** Set a section's date sheet for a school exam: a draft families cannot see yet. */
export async function createSchoolExam(body: Record<string, unknown>): Promise<ExamPlan> {
    return toExamPlan(await api.post("/exams/school-exams", body));
}

/** Change a date sheet; once it is published the families are told what changed. */
export async function updateSchoolExam(
    examId: string,
    body: Record<string, unknown>,
): Promise<ExamPlan> {
    return toExamPlan(await api.patch(`/exams/school-exams/${examId}`, body));
}

/** Publish the date sheet and its syllabus (the class teacher's call). */
export async function publishDateSheet(examId: string): Promise<ExamPlan> {
    return toExamPlan(await api.post(`/exams/school-exams/${examId}/publish`, {}));
}

/** Delete a date sheet that was never published and has no marks. */
export async function deleteSchoolExam(examId: string): Promise<void> {
    await api.delete<void>(`/exams/school-exams/${examId}`);
}

/** Hide a cancelled class test from the list (or bring it back). Nothing is deleted. */
export async function archiveClassTest(examId: string, archive: boolean): Promise<ExamPlan> {
    return toExamPlan(
        await api.post(`/exams/class-tests/${examId}/${archive ? "archive" : "unarchive"}`),
    );
}

/** Call a school exam off; the families are told if its date sheet was published. */
export async function cancelSchoolExam(examId: string): Promise<ExamPlan> {
    return toExamPlan(await api.post(`/exams/school-exams/${examId}/cancel`));
}

/** Hide a date sheet from the list (or bring it back). Nothing is deleted. */
export async function archiveSchoolExam(examId: string, archive: boolean): Promise<ExamPlan> {
    return toExamPlan(
        await api.post(`/exams/school-exams/${examId}/${archive ? "archive" : "unarchive"}`),
    );
}

/** One subject's syllabus. */
export async function getSyllabus(paperId: string): Promise<Syllabus> {
    return toCamel<Syllabus>(await api.get(`/exams/papers/${paperId}/syllabus`));
}

/** Write (or clear, with blank text) one subject's syllabus. */
export async function setSyllabus(
    paperId: string,
    text: string,
    byEmployeeId?: string | null,
): Promise<Syllabus> {
    return toCamel<Syllabus>(
        await api.put(`/exams/papers/${paperId}/syllabus`, {
            syllabus_text: text,
            // left out = unchanged; null = back to the assigned teacher
            ...(byEmployeeId === undefined ? {} : { by_employee_id: byEmployeeId }),
        }),
    );
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
    gradeMode?: "auto" | "na" | "manual",
): Promise<MarksSaved> {
    return toCamel<MarksSaved>(
        await api.post<unknown>(`/exams/papers/${paperId}/marks`, {
            entries,
            ...(gradeMode ? { grade_mode: gradeMode } : {}),
        }),
    );
}

/** Switch a paper's Grade column between NA, Auto and Manual - also after publishing. */
export async function setGradeMode(
    paperId: string,
    gradeMode: "auto" | "na" | "manual",
    grades: { studentId: string; grade: string }[] = [],
): Promise<PaperMarkRow[]> {
    return toCamel<PaperMarkRow[]>(
        await api.post<unknown>(`/exams/papers/${paperId}/grade-mode`, {
            grade_mode: gradeMode,
            grades: grades.map((item) => ({ student_id: item.studentId, grade: item.grade })),
        }),
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
    change: {
        marksObtained: number | null;
        absent?: boolean;
        grade?: string | null;
        reason?: string | null;
    },
): Promise<PaperMarkRow> {
    const payload = await api.patch<unknown>(`/exams/papers/${paperId}/marks/${studentId}`, {
        marks_obtained: change.marksObtained,
        absent: change.absent,
        grade: change.grade ?? null,
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
