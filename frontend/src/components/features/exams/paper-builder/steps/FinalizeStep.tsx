"use client";

// ============================================================
// FinalizeStep — blueprint §1.15 (Step 15)
// Summary snapshot + approve → status approved (demo persists
// via finalizePaper when the backend is reachable).
// ============================================================

import { useState } from "react";
import { Button, Card } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { finalizePaper } from "@/services/exam-builder.service";
import type { PaperBuilderApi } from "../usePaperBuilder";

export default function FinalizeStep({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const [busy, setBusy] = useState(false);
    const s = builder.state;

    async function finalize() {
        setBusy(true);
        await finalizePaper(1); // demo paperId until drafts are persisted server-side
        builder.setStatus("approved");
        setBusy(false);
        push("success", "Paper finalized and approved");
    }

    return (
        <div className="grid gap-3">
            <Card title="Paper summary">
                <div className="grid gap-1 text-sm">
                    <p><b>{s.basics.title}</b> — Class {s.basics.className} {s.basics.subject} ({s.basics.board})</p>
                    <p className="text-muted-foreground">
                        {s.basics.examType} · {s.basics.durationMinutes} min · {s.basics.totalMarks} marks ·{" "}
                        {s.basics.language}
                    </p>
                    <p className="mt-2">
                        Questions: <b>{s.customQuestions.length + s.generatedQuestions.length}</b>{" "}
                        ({s.customQuestions.length} custom + {s.generatedQuestions.length} AI)
                    </p>
                    <p>
                        Marks: <b>{builder.totalPlanned}</b> of {s.basics.totalMarks}{" "}
                        {builder.balanced ? "✅ balanced" : `⚠ off by ${Math.abs(builder.balance)}`}
                    </p>
                    <p className="text-muted-foreground">
                        Chapters: {s.basics.chapters.join(", ") || "—"} · Sources:{" "}
                        {s.sources.length} · Instructions: {s.instructions.length}
                    </p>
                </div>
            </Card>
            <div className="flex items-center gap-2">
                <Button variant="primary" disabled={!builder.balanced} loading={busy} onClick={finalize}>
                    ✔ Approve & finalize
                </Button>
                {s.status === "approved" && (
                    <span className="text-sm text-emerald-700">✅ Approved — proceed to Export</span>
                )}
            </div>
            {!builder.balanced && (
                <p className="text-sm text-amber-700">
                    Balance the Marks Contract before approving.
                </p>
            )}
        </div>
    );
}