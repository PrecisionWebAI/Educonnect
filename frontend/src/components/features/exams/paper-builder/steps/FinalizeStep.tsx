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
    const all = [...s.customQuestions, ...s.generatedQuestions];

    // Blueprint §1.15 — finalize is blocked while ANY of these hold:
    const blockers: string[] = [];
    if (!builder.balanced)
        blockers.push(`Marks Contract off by ${Math.abs(builder.balance)}`);
    if (builder.coverageChecks.some((c) => !c.ok))
        blockers.push("Chapter coverage unmet (Modes B/C)");
    const noAnswer = all.filter((q) => !(q.answer ?? "").trim());
    if (noAnswer.length > 0)
        blockers.push(`${noAnswer.length} question(s) have no expected answer`);
    const visual = new Set(["Diagram", "Map", "Graph", "LabelDiagram"]);
    const missingImage = all.filter(
        (q) => visual.has(q.type) && !q.image?.fileUrl && !q.image?.storageKey,
    );
    if (missingImage.length > 0)
        blockers.push(`${missingImage.length} visual question(s) missing an image`);
    const noSourceRef = all.filter(
        (q) => q.origin === "ai" && q.sourceRefs.length === 0,
    );
    if (noSourceRef.length > 0)
        blockers.push(`${noSourceRef.length} AI question(s) lost their source ref`);
    const canFinalize = blockers.length === 0;

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
            {all.length > 0 && (
                <Card title="Finalize gate (§1.15)">
                    <div className="grid gap-1 text-sm">
                        {blockers.length === 0 ? (
                            <p className="text-emerald-700">✅ All finalize checks passed</p>
                        ) : (
                            blockers.map((b) => (
                                <p key={b} className="text-amber-700">⚠ {b}</p>
                            ))
                        )}
                    </div>
                </Card>
            )}
            <div className="flex items-center gap-2">
                <Button variant="primary" disabled={!canFinalize} loading={busy} onClick={finalize}>
                    ✔ Approve & finalize
                </Button>
                {s.status === "approved" && (
                    <span className="text-sm text-emerald-700">✅ Approved — proceed to Export</span>
                )}
            </div>
            {!canFinalize && (
                <p className="text-sm text-amber-700">
                    Resolve the blockers above before approving.
                </p>
            )}
        </div>
    );
}