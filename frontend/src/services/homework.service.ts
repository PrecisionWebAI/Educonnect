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

export async function getSubmissions(): Promise<SubmissionItem[]> {
    return api.get<SubmissionItem[]>("/homework/submissions");
}

export async function getDiary(): Promise<DiaryEntry[]> {
    return api.get<DiaryEntry[]>("/homework/diary");
}
