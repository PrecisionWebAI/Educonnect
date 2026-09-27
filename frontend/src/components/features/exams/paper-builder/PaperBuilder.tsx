"use client";

// ============================================================
// PaperBuilder — three tabs in the app's standard Tabs style:
//
//   · AI Paper Builder -> the wizard (Basic Details -> ... -> Generate)
//   · Draft            -> generated but not yet saved/approved papers
//                         (continue where you left off)
//   · Paper            -> saved / approved papers, export/download only
//
// The Draft/Paper lists are filtered by Basic Details (class + subject).
// The tabs are always visible, so Builder -> Draft/Paper -> Builder is
// never blocked.
// ============================================================

import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { PAPER_STEPS } from "@/types/exam-builder";
import type { PaperRow } from "@/types/exam-builder";
import { listPapers } from "@/services/exam-builder.service";
import {
    clearPaperBuilderProgress,
    loadPaperBuilderProgress,
    savePaperBuilderProgress,
    usePaperBuilder,
} from "./usePaperBuilder";
import PaperBuilderStepper from "./PaperBuilderStepper";
import BasicsStep from "./steps/BasicsStep";
import SourceStep from "./steps/SourceStep";
import BlueprintStep from "./steps/BlueprintStep";
import GenerateStep from "./steps/GenerateStep";

const TABS = ["AI Paper Builder", "Draft", "Paper"] as const;
type Tab = (typeof TABS)[number];

/* ------------------------------------------------------------
 * Step router — which panel renders for a given step id
 * ---------------------------------------------------------- */

function StepPanel({ id, builder }: { id: string; builder: ReturnType<typeof usePaperBuilder> }) {
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
    const [activeId, setActiveId] = useState(
        () => loadPaperBuilderProgress()?.activeId ?? PAPER_STEPS[0].id,
    );
    const [papers, setPapers] = useState<PaperRow[]>([]);

    const reload = useCallback(async () => setPapers(await listPapers()), []);
    useEffect(() => {
        let alive = true;
        listPapers().then((rows) => {
            if (alive) setPapers(rows);
        });
        return () => {
            alive = false;
        };
    }, []);

    const b = builder.state.basics;

    /** Filter by Basic Details — class and subject must match */
    const matchesBasics = (p: PaperRow) =>
        (!b.className || p.className === b.className) && (!b.subject || p.subject === b.subject);

    const drafts = papers.filter(
        (p) => p.status !== "approved" && p.status !== "published" && matchesBasics(p),
    );
    const finalPapers = papers.filter(
        (p) => (p.status === "approved" || p.status === "published") && matchesBasics(p),
    );

    const idx = PAPER_STEPS.findIndex((s) => s.id === activeId);
    const valid = builder.stepValid(activeId);
    const atLast = idx === PAPER_STEPS.length - 1;

    /** New paper: clear the state and restart the wizard at step 1. Also clear
     *  the stored local progress, or stale selections return on the next visit. */
    function startNewPaper() {
        clearPaperBuilderProgress();
        builder.reset();
        setActiveId(PAPER_STEPS[0].id);
        setTab("AI Paper Builder");
    }

    /** Continue a draft: open the wizard with that paper id */
    function openDraft(p: PaperRow) {
        clearPaperBuilderProgress();
        builder.reset();
        builder.setPaperId(p.id);
        setActiveId(PAPER_STEPS[0].id);
        setTab("AI Paper Builder");
    }

    function downloadPaper(p: PaperRow, format = "PDF") {
        push("success", `Download queued: ${p.title} (${format})`);
    }

    /** Next: save the current selections/status to local progress, then advance. */
    function goNext() {
        if (atLast || !valid) return;
        const nextId = PAPER_STEPS[idx + 1].id;
        savePaperBuilderProgress(builder.state, nextId);
        setActiveId(nextId);
    }

    return (
        <div>
            {/* Tabs (left) + Start new paper (right) — same row; Tabs visual untouched */}
            <div className="relative">
                <Tabs tabs={[...TABS]} active={tab} onChange={(t) => setTab(t as Tab)} />
                {tab === "AI Paper Builder" && (
                    <Button
                        variant="outline"
                        size="sm"
                        className="absolute top-0 right-0"
                        onClick={startNewPaper}
                    >
                        Start new paper
                    </Button>
                )}
            </div>

            {/* ---------- Header row (Draft/Paper only): filter + refresh ---------- */}
            {tab !== "AI Paper Builder" && (
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-muted-foreground text-xs">
                        {`Filtered by Basic Details — Class ${b.className || "—"} · ${
                            b.subject || "—"
                        }`}
                    </p>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                            void reload();
                        }}
                    >
                        Refresh
                    </Button>
                </div>
            )}

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

                    <div className="modal-actions justify-end">
                        {/* Generate is the last step now, so there is nothing after it
                            to advance to — the Export button lives inside the step. */}
                        {!atLast && (
                            <Button variant="primary" disabled={!valid} onClick={goNext}>
                                Next
                            </Button>
                        )}
                        {!atLast && !valid && (
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
