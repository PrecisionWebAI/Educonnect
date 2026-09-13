// ==========================================================
// EduVerse Exam Paper Builder — service layer (blueprint §2.9)
// New additive file — existing exams.service.ts untouched.
// All blueprint endpoints are wrapped; any endpoint not yet
// present on the backend falls back to a local demo generator
// flagged `source: "mock"` so the UI is fully walkable today.
// ==========================================================

import { api } from "@/lib/api/client";
import { distributionToCoverage } from "@/components/features/exams/paper-builder/usePaperBuilder";
import type {
    ImageRef,
    PaperState,
    QuestionDraft,
    SourceLibraryItem,
} from "@/types/exam-builder";

export interface ServiceResult<T> {
    data?: T;
    source: "api" | "mock";
    error?: string;
}

// ---- Content Library (blueprint §1.2.1) ----

export async function getContentLibrary(): Promise<ServiceResult<SourceLibraryItem[]>> {
    try {
        const data = await api.get<SourceLibraryItem[]>("/exams/sources");
        return { data, source: "api" };
    } catch {
        return { source: "mock", data: demoLibrary() };
    }
}

// ---- Paper draft / generate (blueprint §2.9 endpoints) ----

export async function createPaperDraft(
    state: PaperState,
): Promise<ServiceResult<{ paperId: number }>> {
    try {
        const data = await api.post<{ paperId: number }>("/exams/papers", {
            title: state.basics.title,
            total_marks: state.basics.totalMarks,
            blueprint: state.blueprint,
            coverage_mode: state.distribution.mode,
            coverage_plan: distributionToCoverage(
                state.distribution,
                state.basics.totalMarks,
            ),
            part_b: state.customQuestions,
        });
        return { data, source: "api" };
    } catch {
        return { source: "mock", data: { paperId: 1 } };
    }
}

export async function generatePaper(
    state: PaperState,
): Promise<ServiceResult<QuestionDraft[]>> {
    try {
        const data = await api.post<{ questions: QuestionDraft[] }>("/exams/papers/generate", {
            blueprint: state.blueprint,
            coverage_plan: distributionToCoverage(
                state.distribution,
                state.basics.totalMarks,
            ),
            sources: state.sources,
            instructions: state.instructions,
            total_marks: state.basics.totalMarks,
        });
        return { data: data.questions, source: "api" };
    } catch {
        return { source: "mock", data: mockGenerate(state) };
    }
}

export async function addCustomQuestion(
    question: QuestionDraft,
): Promise<ServiceResult<QuestionDraft>> {
    try {
        const data = await api.post<QuestionDraft>("/exams/questions/custom", question);
        return { data, source: "api" };
    } catch {
        return { source: "mock", data: question };
    }
}

export async function updateQuestion(
    paperId: number,
    questionId: string,
    patch: Partial<QuestionDraft>,
): Promise<ServiceResult<QuestionDraft>> {
    try {
        const data = await api.patch<QuestionDraft>(
            `/exams/papers/${paperId}/questions/${questionId}`,
            patch,
        );
        return { data, source: "api" };
    } catch {
        return { source: "mock", data: { ...patch, id: questionId } as QuestionDraft };
    }
}

export async function finalizePaper(paperId: number): Promise<ServiceResult<{ ok: boolean }>> {
    try {
        const data = await api.post<{ ok: boolean }>(`/exams/papers/${paperId}/finalize`);
        return { data, source: "api" };
    } catch {
        return { source: "mock", data: { ok: true } };
    }
}

// ---- Image attach (blueprint §1.10 / §2.6) ----

export async function attachQuestionImage(
    questionId: string,
    image: ImageRef,
): Promise<ServiceResult<ImageRef>> {
    try {
        const data = await api.post<ImageRef>(`/exams/questions/${questionId}/image`, image);
        return { data, source: "api" };
    } catch {
        return { source: "mock", data: image };
    }
}

// ---- Recommended marks heuristic (no backend call needed) ----

export function recommendMarks(
    type: string,
    difficulty: string,
    answerChars?: number,
): number {
    const base: Record<string, number> = {
        MCQ: 1,
        TrueFalse: 1,
        FillBlanks: 1,
        Match: 2,
        AssertionReason: 2,
        MultipleSelect: 2,
        VeryShort: 1,
        Short: 2,
        Long: 4,
        Essay: 5,
        CaseStudy: 5,
        Diagram: 3,
        Map: 2,
        Graph: 3,
        LabelDiagram: 2,
    };
    let m = base[type] ?? 2;
    if (difficulty === "Hard") m += 1;
    if (answerChars && answerChars > 200) m += 1;
    return Math.max(1, Math.min(8, m));
}

// ---- Demo data (used when backend endpoints are not wired yet) ----

function demoLibrary(): SourceLibraryItem[] {
    return [
        {
            id: "lib-1",
            className: "8",
            subject: "Science",
            board: "CBSE",
            chapters: ["Microorganisms", "Crop Production"],
            sourceType: "Book",
            version: 1,
            tags: ["NCERT", "Photosynthesis", "Decomposition"],
        },
        {
            id: "lib-2",
            className: "8",
            subject: "Science",
            board: "CBSE",
            chapters: ["Electricity", "Motion"],
            sourceType: "Teacher notes",
            teacherName: "Mrs. Sharma",
            version: 2,
            tags: ["Circuit", "Force"],
        },
        {
            id: "lib-3",
            className: "10",
            subject: "Mathematics",
            board: "CBSE",
            chapters: ["Trigonometry", "Polynomials"],
            sourceType: "Previous paper",
            version: 1,
            tags: ["Pattern only"],
        },
    ];
}

const DEMO_TOPICS: Record<string, string[]> = {
    Microorganisms: ["Photosynthesis", "Respiration", "Decomposition"],
    "Crop Production": ["Irrigation", "Crop rotation", "Storage"],
    Electricity: ["Circuit", "Ohm's law", "Resistance"],
    Motion: ["Speed", "Velocity", "Acceleration"],
};

function pick<T>(arr: T[]): T {
    return arr[Math.floor(Math.random() * arr.length)];
}

export function mockGenerate(state: PaperState): QuestionDraft[] {
    const questions: QuestionDraft[] = [];
    const total = state.basics.totalMarks;

    // Distribute blueprint sections proportionally; skips overflow to keep Marks Contract
    const aiBudget = total - state.customQuestions.reduce((s, q) => s + q.marks, 0);
    const budgetLeft = Math.max(0, aiBudget);

    let used = 0;
    let idx = 0;

    for (const section of state.blueprint) {
        if (used >= budgetLeft || section.count <= 0) continue;
        for (let i = 0; i < section.count && used < budgetLeft; i++) {
            const marks = section.marksEach;
            if (used + marks > budgetLeft) break;
            used += marks;
            idx += 1;
            const chapters =
                state.basics.chapters.length > 0
                    ? state.basics.chapters
                    : Object.keys(DEMO_TOPICS);
            const chapter = pick(chapters);
            const topics = DEMO_TOPICS[chapter] ?? [chapter];
            const topic = pick(topics);
            questions.push({
                id: `q${idx}`,
                type: section.type,
                text: `${section.type} question on ${topic} — ${chapter} (${section.marksEach} marks).`,
                options:
                    section.type === "MCQ" || section.type === "MultipleSelect"
                        ? ["Option A", "Option B", "Option C", "Option D"]
                        : undefined,
                answer: "Sample answer (" + topic + ").",
                difficulty: pick(["Easy", "Medium", "Hard"] as const),
                bloom: pick(["Remember", "Understand", "Apply", "Analyze"] as const),
                marks,
                topic,
                chapter,
                sourceRefs: [`Page 14 · ${chapter}`],
                locked: false,
                origin: "ai" as const,
                markingScheme: "1 mark per key point",
            });
        }
    }
    return questions;
}