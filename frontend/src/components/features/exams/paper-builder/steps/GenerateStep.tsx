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
    runGeneration,
    type GenerationProgress,
} from "@/services/exam-builder.service";
import { blueprintTotal, type PaperBuilderApi } from "../usePaperBuilder";

export default function GenerateStep({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const [running, setRunning] = useState(false);
    const [elapsed, setElapsed] = useState(0);
    const [error, setError] = useState<string | null>(null);
    /** Job ka summary note — jab AI ne 0 question banaya (jaise part B ne poora
     *  paper bhar diya) to UI chup nahi rehtee, wajah yahan dikhati hai. */
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

        // ---- 1) Draft save (upsert) — backend validation yahin hoti hai ----
        // Marks Contract **server-side** bhi check hota hai: mismatch = 422.
        const saved = await createPaperDraft(builder.state, builder.state.paperId);
        if (saved.source === "mock" || !saved.data) {
            // Backend reachable nahi → koi demo/dummy paper nahi banate.
            stopTimer();
            const msg =
                saved.error ??
                "Backend reachable nahi hai — paper generate nahi ho sakta. Server chalu karke dobara try karein.";
            setError(msg);
            builder.setProgress({ stage: msg, pct: 0, state: "failed" });
            setRunning(false);
            push("error", msg);
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
        // Job ka `result` = graph ka summary (`question_count`, `marks_total`,
        // `ai_budget`, `contract`, `coverage`, `warnings`, `note`). Khaali bhi ho
        // sakta hai — jaise teacher ke part B questions ne poora paper bhar diya
        // (AI budget 0) → tab backend `note`/`warnings` bhejta hai aur UI ko
        // "0 questions" ki asli wajah dikhani chahiye.
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
                : note || "AI ne 0 question banaya",
            pct: 100,
            state: "done",
        });
        setSummaryNote(qs.length === 0 ? note || "AI ne 0 question banaya." : "");
        builder.setStatus("in_review");
        setRunning(false);
        if (qs.length === 0) {
            push("info", note || "AI ne 0 question banaya — wajah upar likhi hai.");
        } else {
            push("success", `Generated ${qs.length} questions`);
        }
    }

    // ---- Marks Contract gate (wahi rule jo server lagata hai) ----
    // Backend `PaperConfigBase` sirf ek cheez maangta hai (RULE #1):
    // **blueprint total == total marks**, warna POST 422/409.
    //
    // Pehle yahan `!builder.balanced` gate tha — aur **wahi "Blocked" ki wajah
    // thi**: `balance = totalMarks − custom − generated`, aur generate se PEHLE
    // koi generated question hota hi nahi. Isliye balance hamesha totalMarks ke
    // barabar rehta tha aur "✨ Generate paper" button kabhi chalta hi nahi tha.
    // Ab gate blueprint par hai (server ke saath 1:1), aur AI ka apna budget
    // (`totalMarks − part B`) sirf info ke liye dikhta hai.
    const blueprintMarks = blueprintTotal(builder.state.blueprint);
    const blueprintOk =
        builder.state.blueprint.length > 0 &&
        blueprintMarks === builder.state.basics.totalMarks;

    if (!blueprintOk) {
        return (
            <div className="rounded-md border border-amber-300 p-4">
                <Badge tone="amber">Blocked</Badge>
                <p className="mt-2 text-sm">
                    Blueprint ka total <b>{blueprintMarks}</b> marks hai, paper ka total{" "}
                    <b>{builder.state.basics.totalMarks}</b> marks. Server isi mismatch par job
                    reject karta hai (Marks Contract) — isliye yahin rok diya. Blueprint step me
                    counts/marks ko &quot;Matched&quot; karo (ya Smart Rebalance dabao), phir
                    Generate.
                </p>
            </div>
        );
    }

    // ---- Gate 4 ka frontend mirror ----
    // Server (`enqueue_generation`) 409 deta hai jab teacher ke part B questions
    // poora total_marks kha jaate hain (AI ke liye 0 marks bache). Wahi baat
    // yahin pehle dikha dete hain — round trip aur 409 ke bajaye.
    if (builder.aiBudget <= 0) {
        return (
            <div className="rounded-md border border-amber-300 p-4">
                <Badge tone="amber">Blocked</Badge>
                <p className="mt-2 text-sm">
                    AI ke liye <b>0 marks</b> bache hain: aapke questions (part B) ={" "}
                    <b>{builder.customMarks}</b> marks, paper total ={" "}
                    <b>{builder.state.basics.totalMarks}</b> marks. Part B questions ke marks kam
                    karo, ya total marks badhao (ya blueprint me AI ko hissa do) — phir Generate
                    chalega.
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
                    Blueprint {blueprintMarks} marks = {builder.customMarks} your questions (part
                    B) + {builder.aiBudget} AI marks
                </p>
                {/* Yahi "stuff" server par jaata hai (draft body: sources +
                    chapters + blueprint + coverage) — AI inhi se banata hai. */}
                <p className="mt-1 text-xs text-muted-foreground">
                    {builder.state.sources.length} source item(s) from the Source step +{" "}
                    {builder.state.basics.chapters.length} chapter(s) will be sent with the
                    blueprint — AI inhi chapters se questions banayega.
                </p>
                {builder.state.basics.chapters.length === 0 && (
                    <p className="mt-1 text-xs text-amber-700">
                        Source step me koi chapter select nahi hai — AI ke paas context nahi
                        hoga aur questions generic aa sakte hain.
                    </p>
                )}
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
            {summaryNote && (
                <div className="rounded-md border border-amber-300 p-3 text-sm">
                    <Badge tone="amber">No AI question</Badge>
                    <p className="mt-2">{summaryNote}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                        AI ne is baar koi question nahi diya (job ka summary upar likha hai).
                        Review step me part B questions dekh lo, ya Generate dobara dabao —
                        progress bar mein asli stage dikhta hai.
                    </p>
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