// ==========================================================
// EduVerse Exam Paper Builder — shared types (blueprint §1–§2)
// New additive file — existing types/index.ts untouched.
// ==========================================================

export type CoverageMode = "auto" | "marks" | "percent";

export type QuestionType =
    | "MCQ"
    | "TrueFalse"
    | "FillBlanks"
    | "Match"
    | "AssertionReason"
    | "MultipleSelect"
    | "VeryShort"
    | "Short"
    | "Long"
    | "Essay"
    | "CaseStudy"
    | "Diagram"
    | "Map"
    | "Graph"
    | "LabelDiagram";

export type Difficulty = "Easy" | "Medium" | "Hard";

export type BloomLevel = "Remember" | "Understand" | "Apply" | "Analyze";

export type PaperStatus = "draft" | "in_review" | "approved" | "published";

export type ImageKind = "photo" | "source" | "ai" | "url" | "bank" | "collage";

export interface ImageRef {
    kind: ImageKind;
    storageKey?: string;
    fileUrl?: string;
    caption?: string;
    altText?: string;
    questionImage?: boolean;
    answerKeyImage?: boolean;
}

export interface BasicDetails {
    className: string;
    subject: string;
    board: string;
    examType: string;
    chapters: string[];
    language: string;
    durationMinutes: number;
    totalMarks: number;
    title: string;
}

export type SourceType = "A" | "B" | "C" | "D" | "E" | "F" | "G";

export interface SourceItem {
    id: string;
    sourceType: SourceType;
    label: string;
    kind: "knowledge" | "pattern";
    strictness: "Strict" | "Flexible" | "Creative";
    chapters: string[];
    teacherName?: string;
    pages?: string;
    tags?: string[];
    // ---- per-type captured detail (blueprint §1.2 addendum) ----
    // Only the fields for the chosen type are filled; the UI shows
    // just the panel for the type picked in the dropdown.
    fileName?: string; // A (PDF) / B (image) — uploaded file name
    fileSize?: string; // human-readable, e.g. "2.4 MB"
    url?: string; // C — website / URL
    urlStatus?: string; // C — result of the "Test" check (demo)
    textExcerpt?: string; // D — pasted text (stored excerpt)
    bankRef?: string; // E — question-bank item id
    libraryEntryId?: string; // G — saved Content Library entry id
}

export interface PaperScope {
    pages?: string;
    chapterWeights: { chapter: string; topic?: string }[];
    includeTopics: string[];
    excludeTopics: string[];
    conceptCoverage: { concept: string; count: number }[];
}

// ---- Distribution plan (blueprint §1.6+§1.7 merged — inside Step 2) ----
// The teacher under CHAPTER-L level assigns marks or % per selected chapter;
// anywhere they leave a gap, the remainder becomes a Random bucket — at the
// CHAPTER-L level (marks not assigned to any chapter) and, inside each
// chapter (opened via its toggle), at the TOPIC level (a chapter's allocation
// not split into topics).

export type DistributionMode = "marks" | "percent";

export interface TopicSplit {
    topic: string;
    assigned: number; // marks (Mode A) or % points (Mode B)
}

export interface ChapterDistribution {
    chapter: string;
    assigned: number; // marks (A) or % (B) — 0 = unassigned → chapter-level Random
    open: boolean; // topic toggle — collapsed by default (chapter level only)
    topics: TopicSplit[];
}

export interface DistributionPlan {
    mode: DistributionMode;
    chapters: ChapterDistribution[];
}

export interface CoverageTopic {
    topic: string;
    targetMarks: number;
}

export interface CoverageChapter {
    chapter: string;
    targetMarks: number; // filled / computed
    auto: boolean;
    topics: CoverageTopic[];
}

export interface CoveragePlan {
    mode: CoverageMode;
    chapters: CoverageChapter[];
    totalAllocated: number;
}

export interface BlueprintSection {
    type: QuestionType;
    count: number;
    marksEach: number;
    hasImage?: boolean;
}

export type Strictness = "Strict" | "Flexible" | "Creative";

export interface PaperConstraints {
    noDuplicates: boolean;
    noAnswerLeak: boolean;
    sourceOnly: boolean;
    minApplication: number;
    minDiagram: number;
    avoidReuse: boolean;
}
export interface Distribution {
    difficulty: { Easy: number; Medium: number; Hard: number }; // %
    bloom: Record<BloomLevel, number>; // %
    chapterWeights: { chapter: string; pct: number }[]; // %
}

export interface QuestionDraft {
    id: string;
    type: QuestionType;
    text: string;
    options?: string[];
    answer?: string;
    difficulty: Difficulty;
    bloom: BloomLevel;
    marks: number;
    topic: string;
    chapter: string;
    image?: ImageRef;
    sourceRefs: string[];
    locked: boolean;
    origin: "ai" | "teacher";
    recommendedMarks?: number;
    markingScheme?: string;
}

export interface QualityCheck {
    id: string;
    label: string;
    status: "pass" | "fail" | "warn";
    reason?: string;
}

export interface PaperBuilderStep {
    id: string;
    title: string;
    group: string;
    stepNo: number;
}

export interface SourceLibraryItem {
    id: string;
    className: string;
    subject: string;
    board: string;
    chapters: string[];
    sourceType: string;
    teacherName?: string;
    version: number;
    tags: string[];
}

export interface PaperState {
    basics: BasicDetails;
    sources: SourceItem[];
    scope: PaperScope;
    distribution: DistributionPlan;
    blueprint: BlueprintSection[];
    constraints: PaperConstraints;
    customQuestions: QuestionDraft[];
    generatedQuestions: QuestionDraft[];
    paperImages: ImageRef[];
    instructions: string[];
    qualityChecks: QualityCheck[];
    status: PaperStatus;
    generationProgress: {
        stage: string;
        pct: number;
        state: "idle" | "running" | "done" | "failed";
    };
}

// ---- Wizard steps (blueprint §1.0 — 9 steps) ----
// Step 1 "Basic Detail" is the paper fields only; sources live in their
// OWN step 2 "Source" (chapter picker + selected chapters + "To save a
// chapter"). Both belong to the "Setup" group.
// The Marks-per-Q, Distributions and Coverage Module steps are merged into
// ONE step — "Exam Blueprint" (step 3) — which now runs, top to bottom:
//   ① Exam Blueprint (sections · counts · marks)
//   ② Distribution   (marks or % per selected chapter + topic splits with
//                     Random buckets at chapter level and topic level)
//   ③ Coverage Module (auto-derived from the Distribution plan)
// Constraints are merged into Instructions & Rules; custom questions +
// images are handled post-generation in Teacher Review.

export const PAPER_STEPS: PaperBuilderStep[] = [
    { id: "basics", title: "Basic Detail", group: "Setup", stepNo: 1 },
    { id: "source", title: "Source", group: "Setup", stepNo: 2 },
    { id: "blueprint", title: "Exam Blueprint", group: "Blueprint", stepNo: 3 },
    { id: "instructions", title: "Instructions & Rules", group: "Blueprint", stepNo: 4 },
    { id: "generate", title: "Generate", group: "Generate", stepNo: 5 },
    { id: "quality", title: "AI Quality Check", group: "Generate", stepNo: 6 },
    { id: "review", title: "Teacher Review", group: "Review", stepNo: 7 },
    { id: "finalize", title: "Finalize", group: "Review", stepNo: 8 },
    { id: "export", title: "Export", group: "Review", stepNo: 9 },
];

export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
    MCQ: "MCQ",
    TrueFalse: "True / False",
    FillBlanks: "Fill in the blanks",
    Match: "Match the following",
    AssertionReason: "Assertion–Reason",
    MultipleSelect: "Multiple-select",
    VeryShort: "Very Short Answer",
    Short: "Short Answer",
    Long: "Long Answer",
    Essay: "Essay",
    CaseStudy: "Case Study",
    Diagram: "Diagram",
    Map: "Map",
    Graph: "Graph",
    LabelDiagram: "Label the diagram",
};

export const DEFAULT_MARKS_BY_TYPE: Record<QuestionType, number> = {
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