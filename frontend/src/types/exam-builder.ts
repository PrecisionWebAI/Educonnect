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
}

export interface PaperScope {
    pages?: string;
    chapterWeights: { chapter: string; topic?: string }[];
    includeTopics: string[];
    excludeTopics: string[];
    conceptCoverage: { concept: string; count: number }[];
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
    coverage: CoveragePlan;
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

// ---- Wizard steps (blueprint §1.0) ----

export const PAPER_STEPS: PaperBuilderStep[] = [
    { id: "basics", title: "Basic Details", group: "Setup", stepNo: 1 },
    { id: "sources", title: "Sources (A–G)", group: "Setup", stepNo: 2 },
    { id: "scope", title: "Content Scope", group: "Content", stepNo: 3 },
    { id: "coverage", title: "Coverage Module", group: "Content", stepNo: 4 },
    { id: "blueprint", title: "Exam Blueprint", group: "Blueprint", stepNo: 5 },
    { id: "marks", title: "Marks per Q", group: "Blueprint", stepNo: 6 },
    { id: "distributions", title: "Distributions", group: "Blueprint", stepNo: 7 },
    { id: "constraints", title: "Constraints", group: "Blueprint", stepNo: 8 },
    { id: "custom", title: "Custom Questions", group: "Author", stepNo: 9 },
    { id: "images", title: "Images", group: "Author", stepNo: 10 },
    { id: "instructions", title: "Instructions", group: "Author", stepNo: 11 },
    { id: "generate", title: "Generate", group: "Generate", stepNo: 12 },
    { id: "quality", title: "AI Quality Check", group: "Generate", stepNo: 13 },
    { id: "review", title: "Teacher Review", group: "Review", stepNo: 14 },
    { id: "finalize", title: "Finalize", group: "Review", stepNo: 15 },
    { id: "export", title: "Export", group: "Review", stepNo: 16 },
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