"use client";

// ============================================================
// GenerateStep — blueprint §1.12
// Marks Contract gate -> draft save -> AI job (polling) -> export.
//
// The step drives the real backend job:
//   1. POST /exams/papers          (draft upsert -> paperId)
//   2. POST /exams/papers/generate (201 queued)
//   3. GET  /exams/papers/{id}/job (poll -> stage + pct)
//   4. GET  /exams/papers/{id}     (part_a.questions)
//
// The local model is slow (2 MCQs ≈ 115 s; a full paper 15–25 min), so the
// progress bar and elapsed timer are essential — without them the app simply
// looks frozen.
// ============================================================

import { useRef, useState } from "react";
import { Button, Badge } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import {
    createPaperDraft,
    describeFailure,
    runGeneration,
    type GenerationProgress,
} from "@/services/exam-builder.service";
import { blueprintTotal, type PaperBuilderApi } from "../usePaperBuilder";
import ExportDialog from "../widgets/ExportDialog";
import InlineAlert from "../widgets/InlineAlert";
import PostGenerationPanel from "../widgets/PostGenerationPanel";

export default function GenerateStep({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const [running, setRunning] = useState(false);
    const [elapsed, setElapsed] = useState(0);
    const [error, setError] = useState<{ title: string; message: string } | null>(null);
    /** The export options popup — Export is a button here, not a wizard step. */
    const [exportOpen, setExportOpen] = useState(false);
    /** The job's summary note. When the AI returns 0 questions (for example
     *  because part B already covers the paper) the UI shows the reason here. */
    const [summaryNote, setSummaryNote] = useState("");
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    function startTimer() {
        const t0 = Date.now();
        setElapsed(0);
        timerRef.current = setInterval(
            () => setElapsed(Math.round((Date.now() - t0) / 1000)),
            1000,
        );
    }
    function stopTimer() {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = null;
    }

    async function run() {
        setRunning(true);
        setError(null);
        setSummaryNote("");
        startTimer();

        // ---- 1) Draft save (upsert) — backend validation happens here ----
        // The Marks Contract is also enforced server-side: a mismatch is a 422.
        const saved = await createPaperDraft(builder.state, builder.state.paperId);
        if (saved.source === "mock" || !saved.data) {
            // The backend is unreachable, so no demo/dummy paper is created.
            // One presentation only: the inline alert below (no toast as well).
            stopTimer();
            const failure = describeFailure(saved);
            setError(failure);
            builder.setProgress({ stage: failure.message, pct: 0, state: "failed" });
            setRunning(false);
            return;
        }

        builder.setPaperId(saved.data.paperId);

        // ---- 2/3) enqueue + poll ----
        const result = await runGeneration(saved.data.paperId, (p: GenerationProgress) => {
            builder.setProgress({
                stage: p.message ? `${p.stage} — ${p.message}` : p.stage,
                pct: p.pct,
                state: p.status === "failed" ? "failed" : "running",
            });
        });
        stopTimer();

        if (!result.data) {
            const failure = describeFailure(result);
            setError(failure);
            builder.setProgress({ stage: failure.message, pct: 0, state: "failed" });
            setRunning(false);
            return;
        }

        const qs = result.data.questions;
        // The job's `result` is the graph summary (`question_count`,
        // `marks_total`, `ai_budget`, `contract`, `coverage`, `warnings`,
        // `note`). It can be empty — for example when the teacher's part B
        // questions already fill the paper (AI budget 0). The backend then
        // sends `note`/`warnings`, and the UI shows the real reason for
        // "0 questions".
        const summary = (result.data.job?.result ?? {}) as {
            question_count?: number;
            marks_total?: number;
            ai_budget?: number;
            warnings?: string[];
            note?: string;
        };
        const note = summary.note || (summary.warnings ?? [])[0] || "";
        builder.setGenerated(qs);
        const marks = qs.reduce((s, q) => s + q.marks, 0);
        builder.setProgress({
            stage: qs.length
                ? `Generated ${qs.length} questions · ${marks} marks`
                : note || "The AI generated 0 questions",
            pct: 100,
            state: "done",
        });
        setSummaryNote(qs.length === 0 ? note || "The AI generated 0 questions." : "");
        builder.setStatus("in_review");
        setRunning(false);
        if (qs.length === 0) {
            push("info", note || "The AI generated 0 questions — see the reason above.");
        } else {
            push("success", `Generated ${qs.length} questions`);
        }
    }

    // ---- Marks Contract gate (the same rule the server applies) ----
    // `PaperConfigBase` requires one thing (RULE #1):
    // **blueprint total == total marks**, otherwise POST returns 422/409.
    //
    // This used to gate on `!builder.balanced`, which caused the "Blocked"
    // state: `balance = totalMarks − custom − generated`, and before generating
    // there are no generated questions, so the balance always equalled
    // totalMarks. The gate now mirrors the server, and the AI budget
    // (`totalMarks − part B`) is shown for information only.
    const blueprintMarks = blueprintTotal(builder.state.blueprint);
    const blueprintOk =
        builder.state.blueprint.length > 0 && blueprintMarks === builder.state.basics.totalMarks;

    if (!blueprintOk) {
        return (
            <div className="rounded-md border border-amber-300 p-4">
                <Badge tone="amber">Blocked</Badge>
                <p className="mt-2 text-sm">
                    The blueprint totals <b>{blueprintMarks}</b> marks while the paper totals{" "}
                    <b>{builder.state.basics.totalMarks}</b> marks. The server rejects a job on this
                    mismatch (Marks Contract), so it is stopped here. Match the counts and marks in
                    the Blueprint step (or use Smart Rebalance), then Generate.
                </p>
            </div>
        );
    }

    // ---- Frontend mirror of gate 4 ----
    // `enqueue_generation` returns 409 when the teacher's part B questions
    // consume the whole total_marks (leaving 0 for the AI). Surfacing it here
    // avoids a round trip and a 409.
    if (builder.aiBudget <= 0) {
        return (
            <div className="rounded-md border border-amber-300 p-4">
                <Badge tone="amber">Blocked</Badge>
                <p className="mt-2 text-sm">
                    <b>0 marks</b> are left for the AI: your questions (part B) ={" "}
                    <b>{builder.customMarks}</b> marks, paper total ={" "}
                    <b>{builder.state.basics.totalMarks}</b> marks. Reduce the marks on your part B
                    questions, increase the total marks, or give the AI a share of the blueprint —
                    then Generate will run.
                </p>
            </div>
        );
    }

    const prog = builder.state.generationProgress;
    /** The summary card below only earns its space once questions exist. */
    const questionCount =
        builder.state.generatedQuestions.length + builder.state.customQuestions.length;
    return (
        <div className="grid gap-3">
            {/* Stays outside the summary card: this warning is actionable BEFORE
                generating, while the card itself now only appears afterwards. */}
            {builder.state.basics.chapters.length === 0 && (
                <p className="rounded-md border border-amber-300 p-3 text-xs text-amber-700">
                    No chapter is selected in the Source step, so the AI has no context and the
                    questions may come out generic.
                </p>
            )}

            {questionCount > 0 && (
                <div className="rounded-md border p-4 text-sm">
                    <p>
                        Ready: <b>{builder.state.basics.title}</b> · Class{" "}
                        {builder.state.basics.className} {builder.state.basics.subject} ·{" "}
                        {builder.state.basics.totalMarks} marks ·{" "}
                        {builder.state.basics.durationMinutes} min
                    </p>
                    <p className="text-muted-foreground mt-1">
                        Blueprint {blueprintMarks} marks = {builder.customMarks} your questions
                        (part B) + {builder.aiBudget} AI marks
                    </p>
                    {/* This is what goes to the server (draft body: sources +
                    chapters + blueprint + coverage); the AI builds from it. */}
                    <p className="text-muted-foreground mt-1 text-xs">
                        {builder.state.sources.length} source item(s) from the Source step and{" "}
                        {builder.state.basics.chapters.length} chapter(s) will be sent with the
                        blueprint — the AI will draw its questions from these chapters.
                    </p>
                    <p className="text-muted-foreground mt-1 text-xs">
                        {builder.state.paperId
                            ? `Backend draft #${builder.state.paperId} — saving again updates the same draft.`
                            : "Clicking Generate saves the draft on the server and starts the AI job."}
                    </p>
                </div>
            )}
            <Button variant="primary" loading={running} onClick={run}>
                {running ? `Generating… ${elapsed}s` : "Generate paper"}
            </Button>
            {prog.state !== "idle" && (
                <div className="rounded-md border p-3">
                    <div className="text-muted-foreground flex justify-between text-xs">
                        <span>{prog.stage}</span>
                        <span>{prog.pct}%</span>
                    </div>
                    <div className="bg-muted mt-1 h-2 w-full overflow-hidden rounded-full">
                        <div
                            className={
                                prog.state === "failed"
                                    ? "h-2 rounded-full bg-red-500 transition-all"
                                    : prog.state === "done"
                                      ? "h-2 rounded-full bg-emerald-500 transition-all"
                                      : "h-2 rounded-full bg-violet-500 transition-all"
                            }
                            style={{
                                width: `${Math.max(prog.pct, prog.state === "running" ? 5 : 0)}%`,
                            }}
                        />
                    </div>
                    {running && (
                        <p className="text-muted-foreground mt-2 text-xs">
                            The local model runs on this machine, so a full paper can take 15–25
                            minutes. There is no need to close the page: the job keeps running on
                            the server and the status is polled every 3 seconds.
                        </p>
                    )}
                </div>
            )}
            {summaryNote && (
                <div className="rounded-md border border-amber-300 p-3 text-sm">
                    <Badge tone="amber">No AI question</Badge>
                    <p className="mt-2">{summaryNote}</p>
                    <p className="text-muted-foreground mt-1 text-xs">
                        The AI returned no questions this time (the job summary is above). Your own
                        questions stay in the review below — press Generate again to retry, and the
                        progress bar shows the real stage.
                    </p>
                </div>
            )}
            {error && <InlineAlert tone="error" title={error.title} message={error.message} />}
            {builder.state.generatedQuestions.length > 0 && (
                <p className="text-sm text-emerald-700">
                    {builder.state.generatedQuestions.length} AI question(s) drafted. Review them
                    below: unlock one to regenerate it with AI or write your own version.
                </p>
            )}

            {/* ---- Review lives here now: unlock / regenerate / write your own ---- */}
            <PostGenerationPanel builder={builder} />

            {/* Export is a button, not a wizard step - the options open in a popup. */}
            <div className="flex justify-end">
                <Button
                    variant="primary"
                    disabled={!builder.balanced}
                    onClick={() => setExportOpen(true)}
                >
                    Export paper
                </Button>
            </div>
            <ExportDialog
                open={exportOpen}
                onClose={() => setExportOpen(false)}
                builder={builder}
            />
        </div>
    );
}
