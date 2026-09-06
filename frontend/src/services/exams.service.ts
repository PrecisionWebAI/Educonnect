import { api } from "@/lib/api/client";
import type {
    ExamMarkingRow,
    ExamScheduleItem,
    PaperDraftFull,
    PaperReviewItem,
    QuestionItem,
} from "@/types";

export async function getQuestionBank(): Promise<QuestionItem[]> {
    return api.get<QuestionItem[]>("/exams/question-bank");
}

export async function getPaperDraftsFull(): Promise<PaperDraftFull[]> {
    return api.get<PaperDraftFull[]>("/exams/paper-drafts-full");
}

export async function getExamSchedule(): Promise<ExamScheduleItem[]> {
    return api.get<ExamScheduleItem[]>("/exams/schedule");
}

export async function getExamMarkings(): Promise<ExamMarkingRow[]> {
    return api.get<ExamMarkingRow[]>("/exams/markings");
}

export async function getExamPaperReviews(): Promise<PaperReviewItem[]> {
    return api.get<PaperReviewItem[]>("/exams/paper-reviews");
}
