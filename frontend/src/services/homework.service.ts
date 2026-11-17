import { api } from "@/lib/api/client";
import type { DiaryEntry, HomeworkItem, SubmissionItem } from "@/types";

export async function getHomeworks(): Promise<HomeworkItem[]> {
    return api.get<HomeworkItem[]>("/homework");
}

/** The assignments set for **one class-section** (the Classroom's Homework tab). */
export async function getSectionHomeworks(sectionId: string): Promise<HomeworkItem[]> {
    return api.get<HomeworkItem[]>(`/homework/section/${sectionId}`);
}

/** What the assign form sends: one assignment for one class-section. */
export interface HomeworkInput {
    title: string;
    description: string;
    sectionId: string;
    subjectId: string;
    teacherId: string;
    /** `YYYY-MM-DD` - the day it is due. */
    dueDate: string;
}

/**
 * Assign homework to one class-section (`POST /homework`).
 *
 * The server checks that the person assigning actually takes that class/subject,
 * so the response is the stored row - the board then shows what was saved.
 */
export async function createHomework(input: HomeworkInput): Promise<HomeworkItem> {
    return api.post<HomeworkItem>("/homework", {
        title: input.title,
        description: input.description,
        section_id: input.sectionId,
        subject_id: input.subjectId,
        teacher_id: input.teacherId,
        due_date: input.dueDate,
    });
}

export async function getSubmissions(sectionId?: string): Promise<SubmissionItem[]> {
    const suffix = sectionId ? `?section_id=${sectionId}` : "";
    return api.get<SubmissionItem[]>(`/homework/submissions${suffix}`);
}

/**
 * Mark one child's assignment as handed in (`POST /homework/submit`).
 *
 * The server stamps `submitted_at` and decides `is_late` from the due date - the
 * browser neither invents the time nor guesses the lateness.
 */
export async function submitHomework(input: {
    homeworkId: string;
    studentId: string;
    contentUrl?: string | null;
}): Promise<void> {
    await api.post(`/homework/submit`, {
        homework_id: input.homeworkId,
        student_id: input.studentId,
        content_url: input.contentUrl ?? null,
    });
}

/**
 * Give one submission a score and/or a remark (`POST /homework/submissions/{id}/feedback`).
 *
 * Refused unless the caller is the assignment's teacher, the class teacher or the
 * office - and the family is told once, which is why the reason/remark is kept.
 */
export async function gradeSubmission(
    submissionId: string,
    input: { marksAwarded?: number | null; feedback?: string | null },
): Promise<SubmissionItem> {
    return api.post<SubmissionItem>(`/homework/submissions/${submissionId}/feedback`, {
        marks_awarded: input.marksAwarded ?? null,
        teacher_feedback: input.feedback ?? null,
    });
}

export async function getDiary(sectionId?: string): Promise<DiaryEntry[]> {
    const suffix = sectionId ? `?section_id=${sectionId}` : "";
    return api.get<DiaryEntry[]>(`/homework/diary${suffix}`);
}

/** Write one line of a class-section's day - its subject, its period and the note. */
export async function createDiaryLog(input: {
    sectionId: string;
    teacherId: string;
    periodId?: string | null;
    subjectId?: string | null;
    date: string;
    note: string;
}): Promise<void> {
    await api.post(`/homework/diary`, {
        section_id: input.sectionId,
        teacher_id: input.teacherId,
        timetableperiod_id: input.periodId ?? null,
        subject_id: input.subjectId ?? null,
        date: input.date,
        note: input.note,
    });
}
