"use client";

// ============================================================
// PostGenerationPanel — everything the teacher does AFTER a paper exists.
//
// It renders inside the Export step on purpose: adding your own question,
// locking one, regenerating one are all review activities, so none of them is
// offered before a paper has actually been generated.
//
// The rules it enforces:
//   · a question must be UNLOCKED before it can be changed (the card disables
//     every mutating action while it is locked)
//   · an unlocked question offers two routes — regenerate with AI, or write
//     your own (the second one turns it into a Custom question)
//   · regenerating sends ONE job covering exactly the unlocked questions the
//     teacher picked; every other question stays byte-for-byte as it was
//
// Failures go through `describeFailure()`, so the teacher reads
// "Access denied — this question is locked..." and never a raw API sentence.
// ============================================================

import { useEffect, useState } from "react";
import { Badge, Button } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import {
    addCustomQuestion,
    describeFailure,
    getJob,
    getPaper,
    regenerateQuestions,
    takeoverQuestion,
    updateQuestion,
} from "@/services/exam-builder.service";
import type { QuestionDraft } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";
import InlineAlert from "../widgets/InlineAlert";
import QuestionCard from "../widgets/QuestionCard";
import QuestionEditorModal from "../widgets/QuestionEditorModal";

/** How often we ask the backend about a running regeneration job. */
const POLL_MS = 5000;

interface Notice {
    tone: "error" | "warning" | "info" | "success";
    title: string;
    message: string;
    /** When set, the alert carries an "Unlock" button for that question. */
    unlockId?: string;
}

function StatChip({ label, value }: { label: string; value: number }) {
    return (
        <div className="rounded-md border px-3 py-2">
            <p className="text-muted-foreground text-xs">{label}</p>
            <p className="text-lg font-semibold">{value}</p>
        </div>
    );
}

export default function PostGenerationPanel({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const s = builder.state;
    const paperId = s.paperId;

    // These are `useCallback`-stable in the hook, so pulling them off `builder`
    // here keeps the polling effect from restarting on every render (`builder`
    // itself is a fresh object each render).
    const {
        applyServerPaper,
        toggleLock,
        upsertQuestion,
        addCustomQuestion: addCustomLocally,
        takeoverQuestion: moveToCustomLocally,
    } = builder;

    const [notice, setNotice] = useState<Notice | undefined>(undefined);
    const [editing, setEditing] = useState<QuestionDraft | undefined>(undefined);
    const [adding, setAdding] = useState(false);
    const [writeOwnTarget, setWriteOwnTarget] = useState<QuestionDraft | undefined>(undefined);
    const [jobId, setJobId] = useState<number | undefined>(undefined);
    const [pendingIds, setPendingIds] = useState<string[]>([]);

    const generating = jobId !== undefined;

    // ---- list + counters -------------------------------------------------
    const aiQuestions = s.generatedQuestions;
    const customQuestions = s.customQuestions;

    /** Only AI questions can be regenerated — a Custom one is the teacher's own. */
    const unlockedAi = aiQuestions.filter((q) => !q.locked);
    const lockedCount = aiQuestions.filter((q) => q.locked).length;
    const totalMarks =
        [...customQuestions, ...aiQuestions].reduce((sum, q) => sum + q.marks, 0);

    // ---- HANDLERS ----

    /** Pull the server's paper straight into state — the server is the truth. */
    function syncFromServer(paper: Parameters<PaperBuilderApi["applyServerPaper"]>[0]) {
        applyServerPaper(paper);
    }

    // ---- lock / unlock: the gate in front of every other change ----------
    async function setLocked(q: QuestionDraft, locked: boolean) {
        if (!paperId) {
            toggleLock(q.id);
            return;
        }
        const res = await updateQuestion(paperId, q.id, { locked });
        if (!res.data) {
            setNotice({ tone: "error", ...describeFailure(res) });
            return;
        }
        // One server payload refreshes both lists, so the lock state can never
        // drift between part_a and part_b.
        syncFromServer(res.data);
        push("success", locked ? "Question locked" : "Question unlocked");
    }

    // ---- regenerate: ONE job for exactly the unlocked questions picked ----
    async function regenerate(ids: string[]) {
        if (!paperId) {
            setNotice({
                tone: "warning",
                title: "Paper not saved yet",
                message: "Generate the paper first, then you can regenerate its questions.",
            });
            return;
        }
        if (ids.length === 0) {
            setNotice({
                tone: "info",
                title: "Nothing to regenerate",
                message: "Unlock the questions you want a new version of, then try again.",
            });
            return;
        }

        const res = await regenerateQuestions(paperId, ids);
        if (!res.data) {
            const failure = describeFailure(res);
            setNotice({
                tone: "error",
                ...failure,
                // One locked question → offer the way out right inside the alert.
                unlockId:
                    res.code === "question_locked" && ids.length === 1 ? ids[0] : undefined,
            });
            return;
        }

        const { job_id, queued, skipped_locked, skipped_unknown } = res.data;
        setJobId(job_id);
        setPendingIds(queued);

        const skipped = skipped_locked.length + skipped_unknown.length;
        if (skipped > 0) {
            setNotice({
                tone: "warning",
                title: "Only some questions were queued",
                message:
                    `${queued.length} question(s) queued. ${skipped} could not be included ` +
                    "because they are still locked.",
            });
        } else {
            setNotice({
                tone: "info",
                title: "Regeneration queued",
                message:
                    `${queued.length} question(s) will be rewritten, and no other question ` +
                    "in the paper will change. This can take a minute or two per question.",
            });
        }
    }

    // ---- polling: refresh the paper the moment the job finishes ----------
    useEffect(() => {
        if (jobId === undefined || paperId === undefined) return;
        let cancelled = false;

        const timer = setInterval(() => {
            void (async () => {
                const res = await getJob(paperId);
                const job = res.data;
                if (cancelled || !job) return;
                if (job.status !== "done" && job.status !== "failed") return;

                clearInterval(timer);
                setJobId(undefined);

                if (job.status === "failed") {
                    setNotice({
                        tone: "error",
                        title: "Regeneration failed",
                        message:
                            job.error ??
                            "The AI could not rewrite these questions. Please try again.",
                    });
                    return;
                }

                const paper = await getPaper(paperId);
                if (cancelled) return;
                // The job rewrote part_a on the server; this pulls the new text in.
                if (paper.data) {
                    applyServerPaper(paper.data);
                    setPendingIds([]);
                }
                setNotice({
                    tone: "success",
                    title: "Regeneration complete",
                    message:
                        "The selected questions were updated. Every other question is unchanged.",
                });
            })();
        }, POLL_MS);

        return () => {
            cancelled = true;
            clearInterval(timer);
        };
        // `applyServerPaper` is `useCallback`-stable, so the interval survives
        // re-renders instead of being torn down and restarted each time.
    }, [jobId, paperId, applyServerPaper]);

    // ---- "Write my own": the AI question becomes a Custom question ------
    async function saveMyOwnVersion(q: QuestionDraft) {
        if (!paperId) {
            moveToCustomLocally(q.id, q);
            return;
        }
        const res = await takeoverQuestion(paperId, q.id, {
            text: q.text,
            answer: q.answer,
            mark: q.marks,
            topic: q.topic,
            chapter: q.chapter,
        });
        if (!res.data) {
            const failure = describeFailure(res);
            setNotice({
                tone: "error",
                ...failure,
                // If the server says it is locked, the unlock is one click away.
                unlockId: res.code === "question_locked" ? q.id : undefined,
            });
            return;
        }
        syncFromServer(res.data);
        setWriteOwnTarget(undefined);
        push("success", "Saved as your own question");
    }

    // ---- add / edit a Custom question -----------------------------------
    async function persistCustom(q: QuestionDraft, isEdit: boolean) {
        if (!paperId) {
            if (isEdit) upsertQuestion(q);
            else addCustomLocally(q);
            return;
        }
        if (isEdit) {
            const res = await updateQuestion(paperId, q.id, {
                mark: q.marks,
                text: q.text,
                answer: q.answer,
                topic: q.topic,
                chapter: q.chapter,
            });
            if (!res.data) {
                setNotice({ tone: "error", ...describeFailure(res) });
                return;
            }
            syncFromServer(res.data);
            push("success", "Question updated");
            return;
        }

        const res = await addCustomQuestion(paperId, q);
        if (!res.data) {
            setNotice({ tone: "error", ...describeFailure(res) });
            return;
        }
        // Re-read so the local list matches the server's part_b exactly.
        const paper = await getPaper(paperId);
        if (paper.data) syncFromServer(paper.data);
        push("success", "Question added to your paper");
    }

    // ---- one editor, three jobs: add · edit · write-my-own --------------
    const editorOpen = adding || Boolean(editing) || Boolean(writeOwnTarget);
    const editorMode = writeOwnTarget ? "writeOwn" : editing ? "edit" : "add";

    function closeEditor() {
        setAdding(false);
        setEditing(undefined);
        setWriteOwnTarget(undefined);
    }

    function handleEditorSave(q: QuestionDraft) {
        if (editorMode === "writeOwn") {
            // An AI question replaced by the teacher — it becomes a Custom one.
            moveToCustomLocally(q.id, q);
            void saveMyOwnVersion(q);
            return;
        }
        const wasEdit = editorMode === "edit";
        upsertQuestion(q);
        void persistCustom(q, wasEdit);
    }

    if (aiQuestions.length === 0 && customQuestions.length === 0) {
        return (
            <div className="grid gap-1 rounded-md border p-4">
                <p className="text-sm font-semibold">Review your paper</p>
                <p className="text-muted-foreground text-sm">
                    Nothing to review yet. Generate the paper first — then you can lock,
                    regenerate or replace individual questions here.
                </p>
            </div>
        );
    }

    return (
        <div className="grid gap-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                    <p className="flex items-center gap-2 text-sm font-semibold">
                        Review your paper
                        {generating && <Badge tone="amber">Regenerating</Badge>}
                    </p>
                    <p className="text-muted-foreground text-xs">
                        Unlock a question to change it — a locked question is frozen.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <Button
                        variant="primary"
                        size="sm"
                        disabled={generating || unlockedAi.length === 0}
                        onClick={() => void regenerate(unlockedAi.map((q) => q.id))}
                    >
                        {generating
                            ? `Regenerating ${pendingIds.length} question(s)...`
                            : `Regenerate ${unlockedAi.length} unlocked with AI`}
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                            setEditing(undefined);
                            setWriteOwnTarget(undefined);
                            setAdding(true);
                        }}
                    >
                        + Add my own question
                    </Button>
                </div>
            </div>

            {notice && (
                <InlineAlert
                    tone={notice.tone}
                    title={notice.title}
                    message={notice.message}
                    actionLabel={notice.unlockId ? "Unlock" : undefined}
                    onAction={
                        notice.unlockId
                            ? () => {
                                  const target = [
                                      ...customQuestions,
                                      ...aiQuestions,
                                  ].find((q) => q.id === notice.unlockId);
                                  if (target) void setLocked(target, false);
                                  setNotice(undefined);
                              }
                            : undefined
                    }
                    onDismiss={() => setNotice(undefined)}
                />
            )}

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <StatChip label="AI questions" value={aiQuestions.length} />
                <StatChip label="Your questions" value={customQuestions.length} />
                <StatChip label="AI locked" value={lockedCount} />
                <StatChip label="AI unlocked" value={unlockedAi.length} />
            </div>

            <p className="text-muted-foreground text-xs">
                {totalMarks} marks in total · only the unlocked questions you pick are
                regenerated, everything else stays as it is
            </p>

            {/* ---- AI questions: the two routes live here ---- */}
            {aiQuestions.length > 0 && (
                <div className="grid gap-2">
                    <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                        Generated by AI
                    </p>
                    {aiQuestions.map((q, i) => (
                        <QuestionCard
                            key={q.id}
                            question={q}
                            index={i + 1}
                            busy={generating}
                            onRegenerate={(x) => void regenerate([x.id])}
                            onWriteOwn={setWriteOwnTarget}
                            onToggleLock={(x) => void setLocked(x, !x.locked)}
                        />
                    ))}
                </div>
            )}

            {/* ---- Custom questions: the teacher's own, numbered ---- */}
            {customQuestions.length > 0 && (
                <div className="grid gap-2">
                    <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                        Your own questions
                    </p>
                    {customQuestions.map((q, i) => (
                        <QuestionCard
                            key={q.id}
                            question={q}
                            index={i + 1}
                            busy={generating}
                            onEdit={(x) => {
                                setWriteOwnTarget(undefined);
                                setEditing(x);
                            }}
                            onToggleLock={(x) => void setLocked(x, !x.locked)}
                        />
                    ))}
                </div>
            )}

            <QuestionEditorModal
                open={editorOpen}
                editing={writeOwnTarget ?? editing}
                title={
                    editorMode === "writeOwn"
                        ? "Write your own version"
                        : editorMode === "edit"
                          ? "Edit question"
                          : "Add your own question"
                }
                totalMarks={s.basics.totalMarks}
                aiBudget={builder.aiBudget}
                availableChapters={s.basics.chapters}
                onClose={closeEditor}
                onSave={handleEditorSave}
            />
        </div>
    );
}
