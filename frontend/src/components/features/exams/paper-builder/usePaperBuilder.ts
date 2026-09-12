// ==========================================================
// EduVerse Paper Builder — wizard state machine + pure math
// Marks Contract: Σ custom + Σ AI == total (and per-chapter in
// coverage Modes B/C). Generate/Finalize are gated on balance.
// ==========================================================

"use client";

import { useCallback, useState } from "react";
import type {
    BasicDetails,
    BlueprintSection,
    CoverageChapter,
    CoverageMode,
    CoveragePlan,
    ImageRef,
    PaperConstraints,
    PaperScope,
    PaperState,
    QuestionDraft,
} from "@/types/exam-builder";
import { recommendMarks } from "@/services/exam-builder.service";

export interface PaperBuilderApi {
    state: PaperState;
    // mutation helpers
    setBasics: (b: Partial<BasicDetails>) => void;
    addSource: (s: PaperState["sources"][number]) => void;
    removeSource: (id: string) => void;
    setScope: (s: Partial<PaperScope>) => void;
    setCoverageMode: (m: CoverageMode) => void;
    updateCoverageChapter: (idx: number, c: Partial<CoverageChapter>) => void;
    addCoverageChapter: (chapter: string) => void;
    removeCoverageChapter: (chapter: string) => void;
    setBlueprint: (sections: BlueprintSection[]) => void;
    setConstraints: (c: Partial<PaperConstraints>) => void;
    addCustomQuestion: (q: QuestionDraft) => void;
    removeCustomQuestion: (id: string) => void;
    setGenerated: (qs: QuestionDraft[]) => void;
    upsertQuestion: (q: QuestionDraft) => void;
    toggleLock: (id: string) => void;
    deleteQuestion: (id: string) => void;
    regenerateQuestion: (id: string) => void;
    attachImageToQuestion: (id: string, image: ImageRef) => void;
    setInstructions: (ins: string[]) => void;
    setProgress: (p: PaperState["generationProgress"]) => void;
    setStatus: (s: PaperState["status"]) => void;
    reset: () => void;
    // derived
    customMarks: number;
    aiMarks: number;
    totalPlanned: number;
    balance: number; // 0 = balanced
    balanced: boolean;
    aiBudget: number;
    coverageChecks: { chapter: string; target: number; got: number; ok: boolean }[];
    stepValid: (stepId: string) => boolean;
    recommendationFor: (q: Omit<QuestionDraft, "id" | "origin" | "locked">) => number;
}

function emptyState(): PaperState {
    return {
        basics: {
            className: "8",
            subject: "Science",
            board: "CBSE",
            examType: "Unit Test",
            chapters: [],
            language: "English",
            durationMinutes: 45,
            totalMarks: 30,
            title: "Untitled Paper",
        },
        sources: [],
        scope: {
            chapterWeights: [],
            includeTopics: [],
            excludeTopics: [],
            conceptCoverage: [],
        },
        coverage: {
            mode: "auto",
            chapters: [],
            totalAllocated: 0,
        },
        blueprint: defaultBlueprint(),
        constraints: {
            noDuplicates: true,
            noAnswerLeak: true,
            sourceOnly: true,
            minApplication: 1,
            minDiagram: 1,
            avoidReuse: true,
        },
        customQuestions: [],
        generatedQuestions: [],
        paperImages: [],
        instructions: [],
        qualityChecks: [],
        status: "draft",
        generationProgress: {
            stage: "idle",
            pct: 0,
            state: "idle",
        },
    };
}

export function defaultBlueprint(): BlueprintSection[] {
    return [
        { type: "MCQ", count: 5, marksEach: 1 },
        { type: "Short", count: 4, marksEach: 2 },
        { type: "Long", count: 2, marksEach: 4 },
        { type: "CaseStudy", count: 1, marksEach: 5 },
        { type: "AssertionReason", count: 2, marksEach: 2 },
    ];
}

// ---- pure helpers (unit-testable) ----

export function sumQuestions(qs: QuestionDraft[]): number {
    return qs.reduce((s, q) => s + q.marks, 0);
}

export function blueprintTotal(sections: BlueprintSection[]): number {
    return sections.reduce((s, sec) => s + sec.count * sec.marksEach, 0);
}

export function coverageAllocated(plan: CoveragePlan): number {
    return plan.chapters.reduce((s, c) => s + c.targetMarks, 0);
}

export function coverageToMarks(
    mode: CoverageMode,
    chapters: CoverageChapter[],
    total: number,
): CoverageChapter[] {
    if (mode !== "percent") return chapters;
    return chapters.map((c) => ({
        ...c,
        targetMarks: Math.round((c.targetMarks / 100) * total),
    }));
}
export function validators(): {
    stepValid: (stepId: string, s: PaperState) => boolean;
    balanceOf: (s: PaperState) => number;
    aiBudgetOf: (s: PaperState) => number;
    checkCoverage: (s: PaperState) => { chapter: string; target: number; got: number; ok: boolean }[];
} {
    function balanceOf(s: PaperState): number {
        const custom = sumQuestions(s.customQuestions);
        const ai = sumQuestions(s.generatedQuestions);
        return s.basics.totalMarks - custom - ai;
    }

    function aiBudgetOf(s: PaperState): number {
        return Math.max(0, s.basics.totalMarks - sumQuestions(s.customQuestions));
    }

    function stepValid(stepId: string, s: PaperState): boolean {
        switch (stepId) {
            case "basics":
                return s.basics.totalMarks > 0 && s.basics.subject.trim().length > 0;
            case "sources":
                return s.sources.length > 0;
            case "coverage": {
                if (s.coverage.mode === "auto") return true;
                return coverageAllocated(s.coverage) === s.basics.totalMarks &&
                    s.coverage.chapters.length > 0;
            }
            case "blueprint":
                return s.blueprint.length > 0 && blueprintTotal(s.blueprint) > 0;
            case "custom":
                return s.customQuestions.every((q) => q.text.trim().length > 0 && q.marks > 0);
            case "review":
                return s.generatedQuestions.length > 0;
            case "finalize":
                return balanceOf(s) === 0;
            default:
                return true;
        }
    }

    function checkCoverage(
        s: PaperState,
    ): { chapter: string; target: number; got: number; ok: boolean }[] {
        if (s.coverage.mode === "auto" || s.coverage.chapters.length === 0) {
            return [{ chapter: "Auto (no per-chapter plan)", target: 0, got: 0, ok: true }];
        }
        const all = [...s.customQuestions, ...s.generatedQuestions];
        return s.coverage.chapters.map((c) => {
            const got = all
                .filter((q) => q.chapter === c.chapter)
                .reduce((sum, q) => sum + q.marks, 0);
            return { chapter: c.chapter, target: c.targetMarks, got, ok: got === c.targetMarks };
        });
    }

    return { stepValid, balanceOf, aiBudgetOf, checkCoverage };
}
export function usePaperBuilder(): PaperBuilderApi {
    const [state, setState] = useState<PaperState>(emptyState);
    const { balanceOf, aiBudgetOf, checkCoverage } = validators();

    const patch = useCallback(
        (fn: (s: PaperState) => PaperState) => setState((s) => fn(s)),
        [],
    );

    const setBasics = useCallback(
        (b: Partial<BasicDetails>) => patch((s) => ({ ...s, basics: { ...s.basics, ...b } })),
        [patch],
    );

    const addSource = useCallback(
        (src: PaperState["sources"][number]) =>
            patch((s) => ({ ...s, sources: [...s.sources, src] })),
        [patch],
    );

    const removeSource = useCallback(
        (id: string) => patch((s) => ({ ...s, sources: s.sources.filter((x) => x.id !== id) })),
        [patch],
    );

    const setScope = useCallback(
        (sc: Partial<PaperScope>) => patch((s) => ({ ...s, scope: { ...s.scope, ...sc } })),
        [patch],
    );

    const setCoverageMode = useCallback(
        (m: CoverageMode) => patch((s) => ({ ...s, coverage: { ...s.coverage, mode: m } })),
        [patch],
    );

    const updateCoverageChapter = useCallback(
        (idx: number, c: Partial<CoverageChapter>) =>
            patch((s) => {
                const chapters = s.coverage.chapters.map((cc, i) =>
                    i === idx ? { ...cc, ...c } : cc,
                );
                return { ...s, coverage: { ...s.coverage, chapters } };
            }),
        [patch],
    );

    const addCoverageChapter = useCallback(
        (chapter: string) =>
            patch((s) => {
                if (s.coverage.chapters.some((c) => c.chapter === chapter)) return s;
                return {
                    ...s,
                    coverage: {
                        ...s.coverage,
                        chapters: [
                            ...s.coverage.chapters,
                            { chapter, targetMarks: 0, auto: false, topics: [] },
                        ],
                    },
                };
            }),
        [patch],
    );

    const removeCoverageChapter = useCallback(
        (chapter: string) =>
            patch((s) => ({
                ...s,
                coverage: {
                    ...s.coverage,
                    chapters: s.coverage.chapters.filter((c) => c.chapter !== chapter),
                },
            })),
        [patch],
    );

    const setBlueprint = useCallback(
        (sections: BlueprintSection[]) => patch((s) => ({ ...s, blueprint: sections })),
        [patch],
    );
const setConstraints = useCallback(
        (c: Partial<PaperConstraints>) =>
            patch((s) => ({ ...s, constraints: { ...s.constraints, ...c } })),
        [patch],
    );

    const addCustomQuestion = useCallback(
        (q: QuestionDraft) => patch((s) => ({ ...s, customQuestions: [...s.customQuestions, q] })),
        [patch],
    );

    const removeCustomQuestion = useCallback(
        (id: string) =>
            patch((s) => ({
                ...s,
                customQuestions: s.customQuestions.filter((q) => q.id !== id),
            })),
        [patch],
    );

    const setGenerated = useCallback(
        (qs: QuestionDraft[]) => patch((s) => ({ ...s, generatedQuestions: qs })),
        [patch],
    );

    const upsertQuestion = useCallback(
        (q: QuestionDraft) =>
            patch((s) => {
                if (q.origin === "teacher") {
                    const exists = s.customQuestions.some((x) => x.id === q.id);
                    return {
                        ...s,
                        customQuestions: exists
                            ? s.customQuestions.map((x) => (x.id === q.id ? q : x))
                            : [...s.customQuestions, q],
                    };
                }
                const exists = s.generatedQuestions.some((x) => x.id === q.id);
                return {
                    ...s,
                    generatedQuestions: exists
                        ? s.generatedQuestions.map((x) => (x.id === q.id ? q : x))
                        : [...s.generatedQuestions, q],
                };
            }),
        [patch],
    );

    const toggleLock = useCallback(
        (id: string) =>
            patch((s) => ({
                ...s,
                generatedQuestions: s.generatedQuestions.map((q) =>
                    q.id === id ? { ...q, locked: !q.locked } : q,
                ),
            })),
        [patch],
    );

    const deleteQuestion = useCallback(
        (id: string) =>
            patch((s) => ({
                ...s,
                generatedQuestions: s.generatedQuestions.filter((q) => q.id !== id),
            })),
        [patch],
    );
const regenerateQuestion = useCallback(
        (id: string) =>
            patch((s) => ({
                ...s,
                generatedQuestions: s.generatedQuestions.map((q) =>
                    q.id === id
                        ? { ...q, text: `${q.text} (regen ${(Date.now() % 1000).toString()})` }
                        : q,
                ),
            })),
        [patch],
    );

    const attachImageToQuestion = useCallback(
        (id: string, image: ImageRef) =>
            patch((s) => ({
                ...s,
                generatedQuestions: s.generatedQuestions.map((q) =>
                    q.id === id ? { ...q, image } : q,
                ),
            })),
        [patch],
    );

    const setInstructions = useCallback(
        (instructions: string[]) => patch((s) => ({ ...s, instructions })),
        [patch],
    );

    const setProgress = useCallback(
        (p: PaperState["generationProgress"]) =>
            patch((s) => ({ ...s, generationProgress: p })),
        [patch],
    );

    const setStatus = useCallback(
        (status: PaperState["status"]) => patch((s) => ({ ...s, status })),
        [patch],
    );

    const reset = useCallback(() => setState(emptyState()), []);

    const stepValid = useCallback(
        (stepId: string) => validators().stepValid(stepId, state),
        [state],
    );

    const customMarks = sumQuestions(state.customQuestions);
    const aiMarks = sumQuestions(state.generatedQuestions);
    const totalPlanned = customMarks + aiMarks;
    const balance = balanceOf(state);
    const balanced = balance === 0;

    const recommendationFor = useCallback(
        (q: Omit<QuestionDraft, "id" | "origin" | "locked">) =>
            recommendMarks(q.type, q.difficulty, q.text.length),
        [],
    );

    return {
        state,
        setBasics,
        addSource,
        removeSource,
        setScope,
        setCoverageMode,
        updateCoverageChapter,
        addCoverageChapter,
        removeCoverageChapter,
        setBlueprint,
        setConstraints,
        addCustomQuestion,
        removeCustomQuestion,
        setGenerated,
        upsertQuestion,
        toggleLock,
        deleteQuestion,
        regenerateQuestion,
        attachImageToQuestion,
        setInstructions,
        setProgress,
        setStatus,
        reset,
        customMarks,
        aiMarks,
        totalPlanned,
        balance,
        balanced,
        aiBudget: aiBudgetOf(state),
        coverageChecks: checkCoverage(state),
        stepValid,
        recommendationFor,
    };
}