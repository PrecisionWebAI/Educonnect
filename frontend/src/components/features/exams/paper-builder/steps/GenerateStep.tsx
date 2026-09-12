"use client";

// ============================================================
// GenerateStep — blueprint §1.12 (Step 12)
// Marks Contract gate → generate with stage progress.
// ============================================================

import { useState } from "react";
import { Button, Badge } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { generatePaper } from "@/services/exam-builder.service";
import type { PaperBuilderApi } from "../usePaperBuilder";

const STAGES = [
    "Parsing sources…",
    "Planning blueprint…",
    "Drafting questions…",
    "Assigning marks & difficulty…",
    "Checking duplicates…",
];

export default function GenerateStep({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const [running, setRunning] = useState(false);

    async function run() {
        setRunning(true);
        for (let i = 0; i < STAGES.length; i++) {
            builder.setProgress({ stage: STAGES[i], pct: Math.round(((i + 1) / STAGES.length) * 90), state: "running" });
            await new Promise((r) => setTimeout(r, 350)); // demo pacing; backend wiring swaps this out
        }
        const res = await generatePaper(builder.state);
        const qs = res.data ?? [];
        builder.setGenerated(qs);
        builder.setProgress({
            stage: `Generated ${qs.length} questions (${res.source === "mock" ? "demo" : "API"})`,
            pct: 100,
            state: "done",
        });
        builder.setStatus("in_review");
        setRunning(false);
        push(res.source === "mock" ? "success" : "success", `Generated ${qs.length} questions`);
    }

    if (!builder.balanced) {
        return (
            <div className="rounded-md border border-amber-300 p-4">
                <Badge tone="amber">Blocked</Badge>
                <p className="mt-2 text-sm">
                    Marks Contract is off by <b>{Math.abs(builder.balance)}</b> mark(s). Fix it in
                    the blueprint, coverage, or custom-question steps before generating.
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
                    {builder.customMarks} custom + {builder.aiBudget} AI budget = balanced ✅
                </p>
            </div>
            <Button variant="primary" loading={running} onClick={run}>
                {running ? "Generating…" : "✨ Generate paper"}
            </Button>
            {prog.state !== "idle" && (
                <div className="rounded-md border p-3">
                    <div className="flex justify-between text-xs text-muted-foreground">
                        <span>{prog.stage}</span>
                        <span>{prog.pct}%</span>
                    </div>
                    <div className="bg-muted mt-1 h-2 w-full overflow-hidden rounded-full">
                        <div
                            className="bg-primary h-2 rounded-full transition-all"
                            style={{ width: `${prog.pct}%` }}
                        />
                    </div>
                </div>
            )}
            {builder.state.generatedQuestions.length > 0 && (
                <p className="text-sm text-emerald-700">
                    ✅ {builder.state.generatedQuestions.length} AI question(s) drafted — review
                    them in Steps 13–14.
                </p>
            )}
        </div>
    );
}