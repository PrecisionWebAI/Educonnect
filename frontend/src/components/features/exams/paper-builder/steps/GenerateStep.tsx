"use client";

// ============================================================
// GenerateStep — blueprint §1.12
// Marks Contract gate → draft save → AI job (polling) → review.
//
// File 20: pehle ye step **fake** staging dikhata tha (setTimeout
// pacing). Ab asli backend job chalti hai:
//   1. POST /exams/papers          (draft upsert → paperId)
//   2. POST /exams/papers/generate (201 queued)
//   3. GET  /exams/papers/{id}/job (poll → stage + pct)
//   4. GET  /exams/papers/{id}     (part_a.questions)
//
// ⚠️ Local Qwen slow hai (2 MCQ ≈ 115 s). Poora paper 15–25 min.
//    Isliye progress bar + elapsed seconds dikhana zaroori hai —
//    warna user samajhta hai app hang ho gaya.
// ============================================================

import { useRef, useState } from "react";
import { Button, Badge } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import {
    createPaperDraft,
    mockGenerate,
    runGeneration,
    type GenerationProgress,
} from "@/services/exam-builder.service";
import type { PaperBuilderApi } from "../usePaperBuilder";

export default function GenerateStep({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const [running, setRunning] = useState(false);
    const [elapsed, setElapsed] = useState(0);
    const [error, setError] = useState<string | null>(null);
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
        startTimer();

        // ---- 1) Draft save (upsert) — backend validation yahin hoti hai ----
        // Marks Contract **server-side** bhi check hota hai: mismatch = 422.
        const saved = await createPaperDraft(builder.state, builder.state.paperId);
        if (saved.source === "mock" || !saved.data) {
            // Backend reachable nahi → demo mode (UI walkable rehta hai)
            stopTimer();
            const demo = mockGenerate(builder.state);
            builder.setGenerated(demo);
            builder.setProgress({
                stage: `Demo mode: ${demo.length} questions (backend offline)`,
                pct: 100,
                state: "done",
            });
            builder.setStatus("in_review");
            setRunning(false);
            push("info", "Backend offline — demo paper banaya gaya.");
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
            const msg = result.error ?? "Generation failed";
            setError(msg);
            builder.setProgress({ stage: msg, pct: 0, state: "failed" });
            setRunning(false);
            push("error", msg);
            return;
        }

        const qs = result.data.questions;
        builder.setGenerated(qs);
        const marks = qs.reduce((s, q) => s + q.marks, 0);
        builder.setProgress({
            stage: `Generated ${qs.length} questions · ${marks} marks`,
            pct: 100,
            state: "done",
        });
        builder.setStatus("in_review");
        setRunning(false);
        push("success", `Generated ${qs.length} questions`);
    }

    if (!builder.balanced) {
        return (
            <div className="rounded-md border border-amber-300 p-4">
                <Badge tone="amber">Blocked</Badge>
                <p className="mt-2 text-sm">
                    Marks Contract is off by <b>{Math.abs(builder.balance)}</b> mark(s). Fix it
                    in the blueprint or coverage steps, or by adding/removing questions (and
                    their marks) in the Review step — then generate.
                </p>
            </div>
        );
    }

    const prog = builder.state.generationProgress;
    return (
        <div className="grid gap-3">
            <div className="rounded-md border p-4 text-sm">
                <p>
                    Ready: <b>{builder.state.basics.title}</b> · Class {builder.state.basics.className}{" "}
                    {builder.state.basics.subject} · {builder.state.basics.totalMarks} marks ·{" "}
                    {builder.state.basics.durationMinutes} min
                </p>
                <p className="mt-1 text-muted-foreground">
                    {builder.customMarks} custom (part B) + {builder.aiBudget} AI budget = balanced ✅
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                    {builder.state.paperId
                        ? `Backend draft #${builder.state.paperId} — dobara save karne par wahi update hoga.`
                        : "Generate dabane par draft server par save hoga, phir AI job chalu hogi."}
                </p>
            </div>
            <Button variant="primary" loading={running} onClick={run}>
                {running ? `Generating… ${elapsed}s` : "✨ Generate paper"}
            </Button>
            {prog.state !== "idle" && (
                <div className="rounded-md border p-3">
                    <div className="flex justify-between text-xs text-muted-foreground">
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
                        <p className="mt-2 text-xs text-muted-foreground">
                            Local model (Qwen) chalta hai — poora paper 15–25 minute le sakta hai.
                            Page band karne ki zaroorat nahi: job server par chalti rehti hai aur
                            hum har 3 second par status poll karte hain.
                        </p>
                    )}
                </div>
            )}
            {error && (
                <div className="rounded-md border border-red-300 p-3 text-sm">
                    <Badge tone="red">Failed</Badge>
                    <p className="mt-2 whitespace-pre-wrap">{error}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                        Wajah upar likhi hai (model missing / timeout / Marks Contract). Theek karke
                        dobara Generate dabao.
                    </p>
                </div>
            )}
            {builder.state.generatedQuestions.length > 0 && (
                <p className="text-sm text-emerald-700">
                    ✅ {builder.state.generatedQuestions.length} AI question(s) drafted — review them
                    in the Teacher Review step, where you can lock/delete/replace them or add your
                    own.
                </p>
            )}
        </div>
    );
}