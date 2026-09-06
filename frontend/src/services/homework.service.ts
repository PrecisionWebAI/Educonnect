import { api } from "@/lib/api/client";
import type { DiaryEntry, HomeworkItem, SubmissionItem } from "@/types";

export async function getHomeworks(): Promise<HomeworkItem[]> {
    return api.get<HomeworkItem[]>("/homework");
}

export async function getSubmissions(): Promise<SubmissionItem[]> {
    return api.get<SubmissionItem[]>("/homework/submissions");
}

export async function getDiary(): Promise<DiaryEntry[]> {
    return api.get<DiaryEntry[]>("/homework/diary");
}
