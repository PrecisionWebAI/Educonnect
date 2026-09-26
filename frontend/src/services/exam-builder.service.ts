// ==========================================================
// EduVerse Exam Paper Builder — service layer (blueprint §2.9)
// New additive file — the only exams API now (/exams/papers*).
//
// File 19: REAL API wiring (Phase 2 backend endpoints).
//   1. createPaperDraft(state)   → POST /exams/papers     (201 → paperId)
//   2. startGeneration(paperId)  → POST /papers/generate  (201 → job)
//   3. getJob(paperId)           → GET  /papers/{id}/job  (polling)
//   4. getPaper(paperId)         → GET  /papers/{id}      (part_a.questions)
//
// ️ Generation **15–25 minute** leti hai (local Qwen). Isliye HTTP
//    request mein intezaar nahi — POST turant 201 deta hai, phir
//    `GET .../job` poll karke progress bar bharte hain.
//
// Mock fallback sirf **network error** par (backend down) — demo mode
// bacha rehta hai, par backend zinda ho to asli AI chalti hai.
// ==========================================================

import { api } from "@/lib/api/client";
import { distributionToCoverage } from "@/components/features/exams/paper-builder/usePaperBuilder";
import type {
    ImageRef,
    PaperRow,
    PaperState,
    QuestionDraft,
    SourceLibraryItem,
} from "@/types/exam-builder";

export interface ServiceResult<T> {
    data?: T;
    source: "api" | "mock";
    error?: string;
    /** Generation ke case mein job record (status/error/trace_id) —
     *  UI ko fail hone ki asli wajah dikhane ke liye. */
    job?: BackendJob;
}

// ---- Backend shapes (snake_case — jo FastAPI bhejta hai) ----
// Ye yahan isliye likhe hain ki backend ke exact field names ek jagah
// dikhein — badalna ho to sirf yahan.

export interface BackendJob {
    id: number;
    paper_id: number | null;
    /** queued | running | done | failed */
    status: string;
    /** {stage, pct, message, startedAt, finishedAt, result, failedAt, …} */
    stages: Record<string, unknown> | null;
    result: Record<string, unknown> | null;
    error: string | null;
    trace_id: string | null;
    model_info: Record<string, unknown> | null;
}

export interface BackendQuestion {
    id: string;
    type: string;
    marks: number;
    difficulty: string;
    bloom: string;
    chapter: string;
    topic: string;
    hasImage?: boolean;
    origin?: string;
    locked?: boolean;
    text: string;
    answer?: string;
    options?: string[];
    markingScheme?: string;
    sourceRefs?: string[];
    incomplete?: boolean;
}

export interface BackendPaper {
    id: number;
    title: string;
    status: string;
    total_marks: number;
    duration_minutes: number;
    /**
     * ⚠️ Backend `part_a` **list** hai (questions), `{questions: [...]}` nahi.
     * Live test se confirm kiya: `part_a = [{id, type, marks, …}, …]`.
     * Dono shapes handle karte hain taaki backend badle to UI na toote.
     */
    part_a: BackendQuestion[] | { questions?: BackendQuestion[] } | null;
    part_b: unknown;
}

/** `part_a` se questions nikalo — list ya dict, dono se. */
export function extractQuestions(partA: BackendPaper["part_a"]): BackendQuestion[] {
    if (!partA) return [];
    if (Array.isArray(partA)) return partA;
    return partA.questions ?? [];
}

/** Draft save ka body — poora teacher context (File 10/11 ke fields). */
function draftBody(state: PaperState) {
    const b = state.basics;
    return {
        title: b.title,
        total_marks: b.totalMarks,
        duration_minutes: b.durationMinutes,
        // ---- context (AI ko chahiye — warna generic question banega) ----
        class_name: b.className,
        subject: b.subject,
        exam_type: b.examType,
        language: b.language,
        chapters: b.chapters,
        // ---- plan ----
        blueprint: state.blueprint,
        coverage_mode:
            state.distribution.mode === "default" ? "auto" : state.distribution.mode,
        coverage_plan: distributionToCoverage(state.distribution, b.totalMarks),
        // ---- teacher ke questions (part_b) + rules + sources ----
        part_b: state.customQuestions,
        sources: state.sources,
        instructions: state.instructions,
        scope: state.scope,
        constraints: state.constraints,
    };
}

// ---- Content Library (blueprint §1.2.1) ----

export async function getContentLibrary(): Promise<ServiceResult<SourceLibraryItem[]>> {
    try {
        const data = await api.get<SourceLibraryItem[]>("/exams/sources");
        return { data, source: "api" };
    } catch {
        // Backend reachable nahi — library khaali (koi demo data nahi)
        return { source: "mock", data: [] };
    }
}

// ---- Source persistence (Phase 3.1 — source → index → vector DB) ----
// Ye teen functions hi "teacher ka source permanently save karna, uska text
// index karna, aur delete par vectors bhi hataana" ka frontend contract hain.

/** Backend source row (FastAPI `SourceRead` ka shape). */
export interface BackendSource {
    id: number;
    title: string;
    sourceType: string;
    kind: string;
    class_name: string;
    subject: string;
    board: string;
    chapters: string[];
    status: string;
    chunk_count: number;
    page_count?: number | null;
    error: string | null;
    url?: string | null;
    content_hash?: string | null;
    /** true = same content pehle se tha → ye response usi (purane) source ka hai */
    deduplicated?: boolean;
}

/** Upload ka response (`POST /exams/sources/upload`). */
export interface UploadSourceResult {
    sourceId: number;
    storageKey: string;
    status: string;
    message?: string;
    deduplicated?: boolean;
}

/** Source ka body — frontend `SourceItem` ke fields hi bhejte hain (§2.9). */
export interface SourceCreateBody {
    title: string;
    sourceType: string;
    label?: string;
    kind?: "knowledge" | "pattern";
    strictness?: string;
    chapters?: string[];
    tags?: string[];
    teacherName?: string;
    url?: string;
    textExcerpt?: string;
    fileName?: string;
    pages?: string;
    bankRef?: string;
    libraryEntryId?: string;
    class_name?: string;
    subject?: string;
    board?: string;
    contentHash?: string;
    /** versioning: is source ne kis purane source ko replace kiya */
    replacesId?: number;
}

/**
 * Text/URL/notes/bank source backend par save karo → background ingest chalu.
 *
 * Same content dobara bheja gaya to backend **wahi source** wapas deta hai
 * (`deduplicated=true`) — dobara embedding nahi hoti.
 */
export async function createSourceItem(
    body: SourceCreateBody,
): Promise<ServiceResult<BackendSource>> {
    try {
        const data = await api.post<BackendSource>("/exams/sources", body);
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "source save failed",
        };
    }
}

/**
 * File (PDF/image) backend par upload karo — multipart form.
 *
 * `api.postForm` use karte hain (JSON `api.post` nahi): multipart mein
 * `Content-Type` boundary ke saath browser set karta hai, hum nahi.
 */
export async function uploadSourceFile(
    file: File,
    meta: {
        sourceType: string;
        title?: string;
        class_name?: string;
        subject?: string;
        board?: string;
        chapters?: string[];
        teacherName?: string;
        /** versioning: is upload ne kis purane source ko replace kiya */
        replaceSourceId?: number;
    },
): Promise<ServiceResult<UploadSourceResult>> {
    const form = new FormData();
    form.append("file", file);
    form.append("sourceType", meta.sourceType);
    form.append("title", meta.title ?? file.name);
    form.append("class_name", meta.class_name ?? "");
    form.append("subject", meta.subject ?? "");
    form.append("board", meta.board ?? "");
    form.append("chapters", (meta.chapters ?? []).join(", "));
    form.append("teacherName", meta.teacherName ?? "");
    if (meta.replaceSourceId) {
        form.append("replaceSourceId", String(meta.replaceSourceId));
    }

    try {
        const data = await api.postForm<UploadSourceResult>("/exams/sources/upload", form);
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "upload failed",
        };
    }
}

/** Ek source ka live status (ingest progress: pending → ingesting → ready). */
export async function getSourceStatus(
    sourceId: number,
): Promise<ServiceResult<BackendSource>> {
    try {
        const data = await api.get<BackendSource>(`/exams/sources/${sourceId}`);
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "status fetch failed",
        };
    }
}

/**
 * Source delete — row **aur** uske vector chunks (backend dono karta hai).
 *
 * ⚠️ Yehi wo step hai jo "deleted source dobara retrieve na ho" guarantee karta
 * hai: DB row delete + Qdrant points delete, dono ek saath.
 */
export async function deleteSourceItem(
    sourceId: number,
): Promise<ServiceResult<{ deleted: boolean; vectorsRemoved: boolean }>> {
    try {
        const data = await api.delete<{ deleted: boolean; vectorsRemoved: boolean }>(
            `/exams/sources/${sourceId}`,
        );
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "source delete failed",
        };
    }
}

// ---- Paper draft save (upsert) ----

type PaperListItem = {
    id: number;
    title: string;
    class_name?: string;
    subject?: string;
    exam_type?: string;
    total_marks: number;
    status: string;
    updated_at: string;
};

/** Teacher ke apne papers (GET /exams/papers) — Draft/Paper tabs. */
export async function listPapers(): Promise<PaperRow[]> {
    try {
        const raw = await api.get<PaperListItem[]>("/exams/papers");
        return raw.map((p) => ({
            id: p.id,
            title: p.title,
            className: p.class_name ?? "",
            subject: p.subject ?? "",
            examType: p.exam_type ?? "",
            totalMarks: p.total_marks,
            status: p.status,
            updatedAt: p.updated_at,
        }));
    } catch {
        return [];
    }
}

export async function createPaperDraft(
    state: PaperState,
    /** diya gaya to **update** (upsert) — warna naya draft banega */
    paperId?: number,
): Promise<ServiceResult<{ paperId: number; status: string }>> {
    try {
        const body = draftBody(state);
        const data = paperId
            ? await api.patch<{ paperId: number; status: string }>(
                  `/exams/papers/${paperId}`,
                  body,
              )
            : await api.post<{ paperId: number; status: string }>("/exams/papers", body);
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            data: { paperId: paperId ?? 1, status: "draft" },
            error: err instanceof Error ? err.message : "save failed",
        };
    }
}

// ---- Generation: enqueue → poll ----

export async function startGeneration(
    paperId: number,
    force = false,
): Promise<ServiceResult<BackendJob>> {
    try {
        const data = await api.post<BackendJob>("/exams/papers/generate", {
            paper_id: paperId,
            force, // true = chal raha duplicate job ignore karke naya banao
        });
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "generate failed",
        };
    }
}

export async function getJob(paperId: number): Promise<ServiceResult<BackendJob>> {
    try {
        const data = await api.get<BackendJob>(`/exams/papers/${paperId}/job`);
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "job poll failed",
        };
    }
}

export async function getPaper(paperId: number): Promise<ServiceResult<BackendPaper>> {
    try {
        const data = await api.get<BackendPaper>(`/exams/papers/${paperId}`);
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "paper fetch failed",
        };
    }
}

/** Backend question → frontend `QuestionDraft` (naming ka farq yahan). */
export function mapBackendQuestion(raw: BackendQuestion): QuestionDraft {
    return {
        id: raw.id,
        type: raw.type as QuestionDraft["type"],
        text: raw.text,
        options: raw.options && raw.options.length > 0 ? raw.options : undefined,
        answer: raw.answer || undefined,
        difficulty: (raw.difficulty || "Medium") as QuestionDraft["difficulty"],
        bloom: (raw.bloom || "Understand") as QuestionDraft["bloom"],
        marks: raw.marks,
        topic: raw.topic || "",
        chapter: raw.chapter || "",
        sourceRefs: raw.sourceRefs ?? [],
        locked: Boolean(raw.locked),
        origin: raw.origin === "teacher" ? "teacher" : "ai",
        markingScheme: raw.markingScheme || undefined,
    };
}

// ---- Full generation cycle: enqueue → poll → fetch paper ----

export interface GenerationProgress {
    status: string; // queued | running | done | failed
    stage: string; // "generating 1/3"
    pct: number;
    message?: string;
    error?: string;
}

export interface RunGenerationOptions {
    intervalMs?: number; // polling gap (default 3000 = 3s)
    timeoutMs?: number; // max wait (default 30 min — local model slow hai)
    force?: boolean; // chal raha job ignore karke naya banao
}

/**
 * Poora generation cycle: enqueue → poll → paper fetch.
 *
 * `onProgress` har poll par bulata hai (UI progress bar ke liye).
 * Questions khaali ho sakte hain agar job fail hua — tab `error` mein
 * asli wajah hoti hai (frontend ko woh **dikhani hi** chahiye, warna
 * teacher dobara Generate dabata hai aur 2 job ban jate hain).
 */
export async function runGeneration(
    paperId: number,
    onProgress?: (p: GenerationProgress) => void,
    opts: RunGenerationOptions = {},
): Promise<ServiceResult<{ questions: QuestionDraft[]; job?: BackendJob }>> {
    const interval = opts.intervalMs ?? 3000;
    const timeout = opts.timeoutMs ?? 30 * 60 * 1000;
    const started = Date.now();

    // 1) enqueue — turant 201 (job queued)
    const queued = await startGeneration(paperId, opts.force ?? false);
    if (queued.source === "mock" || !queued.data) {
        return { source: "mock", error: queued.error ?? "backend unreachable" };
    }

    let job = queued.data;
    onProgress?.({ status: job.status, stage: "Queued", pct: 0 });

    // 2) poll — jab tak queued/running hai
    while (job.status === "queued" || job.status === "running") {
        if (Date.now() - started > timeout) {
            return {
                source: "api",
                job,
                error:
                    "Generation timed out (30 min). Local model slow hai — Ollama aur model check karo.",
            };
        }
        await new Promise((r) => setTimeout(r, interval));

        const polled = await getJob(paperId);
        if (!polled.data) {
            continue; // network hiccup — loop chalta rahe (timeout tak)
        }
        job = polled.data;

        // ⚠️ Backend `stages.stage` nahi bhejta — keys hain:
        //   current ("planning" | "generating" | "completed"),
        //   batch ("MCQ 1-2"), pct, generated, total, done.
        // Live test se confirm kiya (kaccha assume karna = 0% stuck progress).
        const stages = (job.stages ?? {}) as Record<string, unknown>;
        const batch = stages.batch ? String(stages.batch) : "";
        onProgress?.({
            status: job.status,
            stage: batch
                ? `${String(stages.current ?? job.status)} · ${batch}`
                : String(stages.current ?? job.status),
            pct: Number(stages.pct ?? 0),
            message:
                stages.generated !== undefined
                    ? `${stages.generated}/${stages.total ?? "?"} questions`
                    : undefined,
        });
    }

    if (job.status === "failed") {
        return { source: "api", job, error: job.error ?? "Generation failed" };
    }

    // 3) done — paper se part_a.questions nikalo
    const paper = await getPaper(paperId);
    if (paper.source === "mock" || !paper.data) {
        return { source: "api", job, error: paper.error ?? "paper fetch failed" };
    }
    const rawQs = extractQuestions(paper.data.part_a);
    return {
        source: "api",
        job,
        data: { questions: rawQs.map(mapBackendQuestion), job },
    };
}

// ---- Teacher ka custom question (part_b) ----

export async function addCustomQuestion(
    paperId: number,
    question: QuestionDraft,
): Promise<ServiceResult<BackendQuestion>> {
    try {
        // Backend `CustomQuestionCreate {paper_id, question}` maangta hai —
        // pehle hum seedha question bhej rahe the (contract mismatch).
        const data = await api.post<BackendQuestion>("/exams/questions/custom", {
            paper_id: paperId,
            question: {
                id: question.id,
                type: question.type,
                marks: question.marks,
                difficulty: question.difficulty,
                bloom: question.bloom,
                chapter: question.chapter,
                topic: question.topic,
                text: question.text,
                answer: question.answer,
                options: question.options,
                markingScheme: question.markingScheme,
                locked: question.locked,
            },
        });
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "custom question failed",
        };
    }
}

// ---- Question patch (lock / edit / regenerate) ----

export interface QuestionPatchBody {
    mark?: number;
    text?: string;
    answer?: string;
    topic?: string;
    chapter?: string;
    locked?: boolean;
    /** true = AI se dobara banwao (backend ek job banata hai) */
    regenerate?: boolean;
}

export async function updateQuestion(
    paperId: number,
    questionId: string,
    patch: QuestionPatchBody,
): Promise<ServiceResult<BackendPaper>> {
    try {
        const data = await api.patch<BackendPaper>(
            `/exams/papers/${paperId}/questions/${questionId}`,
            patch,
        );
        return { data, source: "api" };
    } catch (err) {
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "patch failed",
        };
    }
}

// ---- Finalize (hard gate backend par) ----

export async function finalizePaper(paperId: number): Promise<ServiceResult<BackendPaper>> {
    try {
        const data = await api.post<BackendPaper>(`/exams/papers/${paperId}/finalize`);
        return { data, source: "api" };
    } catch (err) {
        // 409 = Marks Contract / coverage gate fail (backend ka saaf message)
        return {
            source: "mock",
            error: err instanceof Error ? err.message : "finalize failed",
        };
    }
}

// ---- Suggested marks (custom question modal) ----

export interface MarksSuggestion {
    marks: number;
    base?: number;
    source: "rules" | "llm";
    reasons?: string[];
}

/**
 * Backend se suggested marks. Default **rules-only** (instant, free).
 * `useLlm=true` = judge model se second opinion (slow ~60s, ±1 clamp).
 * Backend na mile to local heuristic (`recommendMarks`) — UI kabhi block nahi hota.
 */
export async function suggestMarks(
    type: string,
    difficulty: string,
    text: string,
    useLlm = false,
): Promise<MarksSuggestion> {
    try {
        const data = await api.post<MarksSuggestion>("/exams/questions/recommend-marks", {
            type,
            difficulty,
            text,
            use_llm: useLlm,
        });
        return data;
    } catch {
        return {
            marks: recommendMarks(type, difficulty, text.length),
            source: "rules",
            reasons: ["Offline heuristic (backend reachable nahi tha)"],
        };
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

