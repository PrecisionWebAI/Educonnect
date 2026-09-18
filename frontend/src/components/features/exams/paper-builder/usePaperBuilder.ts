// ==========================================================
// EduVerse Paper Builder — wizard state machine + pure math
// Marks Contract: Σ custom + Σ AI == total. The Distribution
// plan (marks/% per chapter + topic splits with Random buckets)
// replaces the old separate Marks/Distributions/Coverage steps.
// Generate/Finalize are gated on balance.
// ==========================================================

"use client";

import { useCallback, useState } from "react";
import type {
    BasicDetails,
    BlueprintSection,
    ChapterDistribution,
    CoverageChapter,
    CoverageMode,
    CoveragePlan,
    DistributionMode,
    DistributionPlan,
    ImageRef,
    PaperConstraints,
    PaperScope,
    PaperState,
    QuestionDraft,
    TopicSplit,
} from "@/types/exam-builder";
import { recommendMarks } from "@/services/exam-builder.service";

export interface PaperBuilderApi {
    state: PaperState;
    // mutation helpers
    setBasics: (b: Partial<BasicDetails>) => void;
    addSource: (s: PaperState["sources"][number]) => void;
    removeSource: (id: string) => void;
    setScope: (s: Partial<PaperScope>) => void;
    setDistributionMode: (m: DistributionMode) => void;
    updateChapterDistribution: (idx: number, c: Partial<ChapterDistribution>) => void;
    toggleChapterTopics: (chapter: string) => void;
    addTopic: (chapter: string, topic: string) => void;
    updateTopic: (chapter: string, topicIdx: number, t: Partial<TopicSplit>) => void;
    removeTopic: (chapter: string, topicIdx: number) => void;
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
        distribution: {
            mode: "marks",
            chapters: [],
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

// ---- Distribution plan math (blueprint §1.6/§1.7 merged) ----

export function distributionAllocated(dist: DistributionPlan): number {
    return dist.chapters.reduce((s, c) => s + c.assigned, 0);
}

export function topicAllocated(c: ChapterDistribution): number {
    return c.topics.reduce((n, t) => n + t.assigned, 0);
}

/** Chapter-level Random bucket — allocation left unassigned to any chapter
 *  (marks mode: Total Marks − Σ; percent mode: 100% − Σ). */
export function chapterLevelRandom(dist: DistributionPlan, totalMarks: number): number {
    const cap = dist.mode === "marks" ? totalMarks : 100;
    return Math.max(0, Number((cap - distributionAllocated(dist)).toFixed(2)));
}

/** Topic-level Random bucket for ONE chapter — its allocation not split
 *  into topics (leftover goes to "Random inside topic selection"). */
export function topicLevelRandom(c: ChapterDistribution): number {
    return Math.max(0, Number((c.assigned - topicAllocated(c)).toFixed(2)));
}

/** Derived coverage (marks-based) from the distribution plan — the form that
 *  feeds generation, the coverage charts and the per-chapter checks. */
export function distributionToCoverage(dist: DistributionPlan, totalMarks: number): CoveragePlan {
    const chapters: CoverageChapter[] = dist.chapters.map((c) => ({
        chapter: c.chapter,
        targetMarks:
            dist.mode === "marks" ? c.assigned : Math.round((c.assigned / 100) * totalMarks),
        auto: c.assigned === 0,
        topics: c.topics.map((t) => ({
            topic: t.topic,
            targetMarks:
                dist.mode === "marks" ? t.assigned : Math.round((t.assigned / 100) * totalMarks),
        })),
    }));
    return {
        mode: "marks",
        chapters,
        totalAllocated: chapters.reduce((s, c) => s + c.targetMarks, 0),
    };
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

    function distributionValid(s: PaperState): boolean {
        const cap = s.distribution.mode === "marks" ? s.basics.totalMarks : 100;
        if (distributionAllocated(s.distribution) > cap) return false;
        return s.distribution.chapters.every((c) => topicAllocated(c) <= c.assigned);
    }

    function stepValid(stepId: string, s: PaperState): boolean {
        switch (stepId) {
            case "basics":
                return s.basics.totalMarks > 0 && s.basics.subject.trim().length > 0;
            case "blueprint":
                return (
                    s.blueprint.length > 0 &&
                    blueprintTotal(s.blueprint) > 0 &&
                    blueprintTotal(s.blueprint) === s.basics.totalMarks &&
                    distributionValid(s)
                );
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
        const plan = distributionToCoverage(s.distribution, s.basics.totalMarks);
        if (distributionAllocated(s.distribution) === 0 || plan.chapters.length === 0) {
            return [{ chapter: "Auto (all marks via Random)", target: 0, got: 0, ok: true }];
        }
        const all = [...s.customQuestions, ...s.generatedQuestions];
        return plan.chapters.map((c) => {
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
        (b: Partial<BasicDetails>) =>
            patch((s) => {
                const basics = { ...s.basics, ...b };
                // keep distribution rows in step with the selected chapters
                const keep = s.distribution.chapters.filter((c) =>
                    basics.chapters.includes(c.chapter),
                );
                const have = new Set(keep.map((c) => c.chapter));
                const added = basics.chapters
                    .filter((c) => !have.has(c))
                    .map((c) => ({ chapter: c, assigned: 0, open: false, topics: [] }));
                return {
                    ...s,
                    basics,
                    distribution: { ...s.distribution, chapters: [...keep, ...added] },
                };
            }),
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

    const setDistributionMode = useCallback(
        (m: DistributionMode) =>
            patch((s) => ({ ...s, distribution: { ...s.distribution, mode: m } })),
        [patch],
    );

    const updateChapterDistribution = useCallback(
        (idx: number, c: Partial<ChapterDistribution>) =>
            patch((s) => ({
                ...s,
                distribution: {
                    ...s.distribution,
                    chapters: s.distribution.chapters.map((cc, i) =>
                        i === idx ? { ...cc, ...c } : cc,
                    ),
                },
            })),
        [patch],
    );

    const toggleChapterTopics = useCallback(
        (chapter: string) =>
            patch((s) => ({
                ...s,
                distribution: {
                    ...s.distribution,
                    chapters: s.distribution.chapters.map((c) =>
                        c.chapter === chapter ? { ...c, open: !c.open } : c,
                    ),
                },
            })),
        [patch],
    );

    const addTopic = useCallback(
        (chapter: string, topic: string) =>
            patch((s) => ({
                ...s,
                distribution: {
                    ...s.distribution,
                    chapters: s.distribution.chapters.map((c) =>
                        c.chapter === chapter
                            ? { ...c, topics: [...c.topics, { topic, assigned: 0 }] }
                            : c,
                    ),
                },
            })),
        [patch],
    );

    const updateTopic = useCallback(
        (chapter: string, topicIdx: number, t: Partial<TopicSplit>) =>
            patch((s) => ({
                ...s,
                distribution: {
                    ...s.distribution,
                    chapters: s.distribution.chapters.map((c) =>
                        c.chapter === chapter
                            ? {
                                  ...c,
                                  topics: c.topics.map((tt, i) =>
                                      i === topicIdx ? { ...tt, ...t } : tt,
                                  ),
                              }
                            : c,
                    ),
                },
            })),
        [patch],
    );

    const removeTopic = useCallback(
        (chapter: string, topicIdx: number) =>
            patch((s) => ({
                ...s,
                distribution: {
                    ...s.distribution,
                    chapters: s.distribution.chapters.map((c) =>
                        c.chapter === chapter
                            ? { ...c, topics: c.topics.filter((_, i) => i !== topicIdx) }
                            : c,
                    ),
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
        setDistributionMode,
        updateChapterDistribution,
        toggleChapterTopics,
        addTopic,
        updateTopic,
        removeTopic,
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