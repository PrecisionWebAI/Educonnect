"use client";

// ============================================================
// PaperBuilder — app ki standard Tabs style me **teen tabs**:
//
//   · AI Paper Builder → wizard (Basic Details -> ... -> Export)
//   · Draft            → generate hue par finalize/save NAHI hue papers
//                        (continue karke aage badha sakte ho)
//   · Paper            → saved / approved papers — sirf export/download
//
// Draft/Paper list **Basic Details (class + subject)** se filter hoti hai.
// Tabs hamesha dikhte hain — isliye Builder se Draft/Paper aur wapas Builder
// jaana kabhi blocked nahi hota.
// ============================================================

import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { PAPER_STEPS } from "@/types/exam-builder";
import type { PaperRow } from "@/types/exam-builder";
import { listPapers } from "@/services/exam-builder.service";
import { usePaperBuilder } from "./usePaperBuilder";
import PaperBuilderStepper from "./PaperBuilderStepper";
import BasicsStep from "./steps/BasicsStep";
import SourceStep from "./steps/SourceStep";
import BlueprintStep from "./steps/BlueprintStep";
import GenerateStep from "./steps/GenerateStep";
import ReviewStep from "./steps/ReviewStep";
import ExportStep from "./steps/ExportStep";

const TABS = ["AI Paper Builder", "Draft", "Paper"] as const;
type Tab = (typeof TABS)[number];

/* ------------------------------------------------------------
 * Step router — konsa panel kis step id par render hoga
 * ---------------------------------------------------------- */

function StepPanel({
    id,
    builder,
}: {
    id: string;
    builder: ReturnType<typeof usePaperBuilder>;
}) {
    switch (id) {
        case "basics":
            return <BasicsStep builder={builder} />;
        case "source":
            return <SourceStep builder={builder} />;
        case "blueprint":
            return (
                <BlueprintStep
                    blueprint={builder.state.blueprint}
                    totalMarks={builder.state.basics.totalMarks}
                    onChange={builder.setBlueprint}
                    builder={builder}
                />
            );
        case "generate":
            return <GenerateStep builder={builder} />;
        case "review":
            return <ReviewStep builder={builder} />;
        case "export":
            return <ExportStep builder={builder} />;
        default:
            return null;
    }
}

function statusTone(status: string): "green" | "amber" | "muted" {
    if (status === "approved" || status === "published") return "green";
    if (status === "in_review") return "amber";
    return "muted";
}

/* ------------------------------------------------------------
 * Draft / Paper list
 * ---------------------------------------------------------- */

function PaperListRows({
    rows,
    mode,
    onContinue,
    onDownload,
}: {
    rows: PaperRow[];
    mode: "draft" | "paper";
    onContinue: (p: PaperRow) => void;
    onDownload: (p: PaperRow) => void;
}) {
    if (rows.length === 0) {
        return (
            <p className="text-muted-foreground rounded-md border border-dashed p-6 text-center text-sm">
                {mode === "draft"
                    ? "No unfinished drafts for this class/subject yet."
                    : "No saved/approved papers for this class/subject yet."}
            </p>
        );
    }
    return (
        <div className="grid gap-2">
            {rows.map((p) => (
                <div key={p.id} className="flex flex-wrap items-center gap-3 rounded-md border p-3">
                    <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{p.title}</p>
                        <p className="text-muted-foreground text-xs">
                            {[p.className, p.subject, p.examType].filter(Boolean).join(" · ")}
                            {p.totalMarks ? ` · ${p.totalMarks} marks` : ""}
                        </p>
                    </div>
                    <Badge tone={statusTone(p.status)}>{p.status}</Badge>
                    {mode === "draft" ? (
                        <Button variant="outline" size="sm" onClick={() => onContinue(p)}>
                            Continue →
                        </Button>
                    ) : (
                        <>
                            <Button variant="outline" size="sm" onClick={() => onDownload(p)}>
                                PDF
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => onDownload(p)}>
                                DOCX
                            </Button>
                        </>
                    )}
                </div>
            ))}
        </div>
    );
}

/* ------------------------------------------------------------
 * Main
 * ---------------------------------------------------------- */

export default function PaperBuilder() {
    const builder = usePaperBuilder();
    const { push } = useToast();

    const [tab, setTab] = useState<Tab>("AI Paper Builder");
    const [activeId, setActiveId] = useState(PAPER_STEPS[0].id);
    const [papers, setPapers] = useState<PaperRow[]>([]);

    const reload = useCallback(async () => setPapers(await listPapers()), []);
    useEffect(() => {
        void reload();
    }, [reload]);

    const b = builder.state.basics;

    /** Basic Details se filter — class + subject match hone chahiye */
    const matchesBasics = (p: PaperRow) =>
        (!b.className || p.className === b.className) &&
        (!b.subject || p.subject === b.subject);

    const drafts = papers.filter(
        (p) => p.status !== "approved" && p.status !== "published" && matchesBasics(p),
    );
    const finalPapers = papers.filter(
        (p) => (p.status === "approved" || p.status === "published") && matchesBasics(p),
    );

    const idx = PAPER_STEPS.findIndex((s) => s.id === activeId);
    const valid = builder.stepValid(activeId);
    const atLast = idx === PAPER_STEPS.length - 1;

    /** Naya paper — state saaf, wizard step 1 se */
    function startNewPaper() {
        builder.reset();
        setActiveId(PAPER_STEPS[0].id);
        setTab("AI Paper Builder");
    }

    /** Draft continue — usi paper id ke saath wizard kholo */
    function openDraft(p: PaperRow) {
        builder.reset();
        builder.setPaperId(p.id);
        setActiveId(PAPER_STEPS[0].id);
        setTab("AI Paper Builder");
    }

    function downloadPaper(p: PaperRow, format = "PDF") {
        push("success", `Download queued: ${p.title} (${format})`);
    }

    return (
        <div>
            <Tabs tabs={[...TABS]} active={tab} onChange={(t) => setTab(t as Tab)} />

            {/* ---------- Header row: context + primary action ---------- */}
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <p className="text-muted-foreground text-xs">
                    {tab === "AI Paper Builder"
                        ? "Build a new paper step by step — class/subject, sources, blueprint, then AI generation."
                        : `Filtered by Basic Details — Class ${b.className || "—"} · ${
                              b.subject || "—"
                          }`}
                </p>
                {tab === "AI Paper Builder" ? (
                    <Button variant="outline" size="sm" onClick={startNewPaper}>
                        ↺ Start new paper
                    </Button>
                ) : (
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                            void reload();
                        }}
                    >
                        Refresh
                    </Button>
                )}
            </div>

            {/* ---------- TAB 1: wizard ---------- */}
            {tab === "AI Paper Builder" && (
                <div className="grid gap-4">
                    <PaperBuilderStepper
                        activeId={activeId}
                        onSelect={setActiveId}
                        isValid={builder.stepValid}
                    />

                    <div className="rounded-md border p-4">
                        <StepPanel id={activeId} builder={builder} />
                    </div>

                    <div className="modal-actions">
                        <Button
                            variant="outline"
                            disabled={idx <= 0}
                            onClick={() => setActiveId(PAPER_STEPS[Math.max(0, idx - 1)].id)}
                        >
                            ← Back
                        </Button>
                        <Button
                            variant="primary"
                            disabled={atLast || !valid}
                            onClick={() =>
                                setActiveId(
                                    PAPER_STEPS[Math.min(PAPER_STEPS.length - 1, idx + 1)].id,
                                )
                            }
                        >
                            Next: {PAPER_STEPS[Math.min(PAPER_STEPS.length - 1, idx + 1)].title} →
                        </Button>
                        {!valid && (
                            <span className="text-muted-foreground self-center text-xs">
                                Complete this step to continue (or jump via the stepper).
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* ---------- TAB 2: unfinished drafts ---------- */}
            {tab === "Draft" && (
                <PaperListRows
                    rows={drafts}
                    mode="draft"
                    onContinue={openDraft}
                    onDownload={downloadPaper}
                />
            )}

            {/* ---------- TAB 3: saved / approved papers ---------- */}
            {tab === "Paper" && (
                <PaperListRows
                    rows={finalPapers}
                    mode="paper"
                    onContinue={openDraft}
                    onDownload={downloadPaper}
                />
            )}
        </div>
    );
}