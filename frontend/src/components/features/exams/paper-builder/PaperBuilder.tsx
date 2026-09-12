"use client";

// ============================================================
// PaperBuilder — the 16-step wizard container (blueprint §1.0)
// Stepper + per-step validation + navigation + live MarksBar.
// ============================================================

import { useEffect, useState } from "react";
import { Button } from "@/components/ui";
import { PAPER_STEPS } from "@/types/exam-builder";
import { usePaperBuilder } from "./usePaperBuilder";
import MarksBar from "./widgets/MarksBar";
import PaperBuilderStepper from "./PaperBuilderStepper";
import BasicsStep from "./steps/BasicsStep";
import SourcesStep from "./steps/SourcesStep";
import ScopeStep from "./steps/ScopeStep";
import CoverageStep from "./steps/CoverageStep";
import BlueprintStep from "./steps/BlueprintStep";
import { ConstraintsStep, DistributionsStep, MarksStep } from "./steps/BlueprintStepsB";
import CustomQuestionsStep from "./steps/CustomQuestionsStep";
import ImagesStep from "./steps/ImagesStep";
import InstructionsStep from "./steps/InstructionsStep";
import GenerateStep from "./steps/GenerateStep";
import QualityStep from "./steps/QualityStep";
import ReviewStep from "./steps/ReviewStep";
import FinalizeStep from "./steps/FinalizeStep";
import ExportStep from "./steps/ExportStep";

function StepPanel({
    id,
    builder,
    chapters,
}: {
    id: string;
    builder: ReturnType<typeof usePaperBuilder>;
    chapters: string[];
}) {
    switch (id) {
        case "basics":
            return <BasicsStep builder={builder} />;
        case "sources":
            return <SourcesStep builder={builder} />;
        case "scope":
            return <ScopeStep builder={builder} />;
        case "coverage":
            return <CoverageStep builder={builder} availableChapters={chapters} />;
        case "blueprint":
            return (
                <BlueprintStep
                    blueprint={builder.state.blueprint}
                    totalMarks={builder.state.basics.totalMarks}
                    onChange={builder.setBlueprint}
                />
            );
        case "marks":
            return <MarksStep builder={builder} />;
        case "distributions":
            return <DistributionsStep builder={builder} />;
        case "constraints":
            return (
                <ConstraintsStep
                    constraints={builder.state.constraints}
                    onChange={builder.setConstraints}
                />
            );
        case "custom":
            return <CustomQuestionsStep builder={builder} />;
        case "images":
            return <ImagesStep builder={builder} />;
        case "instructions":
            return <InstructionsStep builder={builder} />;
        case "generate":
            return <GenerateStep builder={builder} />;
        case "quality":
            return <QualityStep builder={builder} />;
        case "review":
            return <ReviewStep builder={builder} />;
        case "finalize":
            return <FinalizeStep builder={builder} />;
        case "export":
            return <ExportStep builder={builder} />;
        default:
            return null;
    }
}

export default function PaperBuilder() {
    const builder = usePaperBuilder();
    const [activeId, setActiveId] = useState("basics");
    const [chapters, setChapters] = useState<string[]>([]);

    // Content Library chapters (demo fallback) ∪ user-entered chapters
    useEffect(() => {
        let alive = true;
        import("@/services/exam-builder.service").then(({ getContentLibrary }) =>
            getContentLibrary().then((res) => {
                if (!alive) return;
                const lib = (res.data ?? []).flatMap((i) => i.chapters);
                setChapters([...new Set([...lib, ...builder.state.basics.chapters])]);
            }),
        );
        return () => {
            alive = false;
        };
    }, [builder.state.basics.chapters]);

    const idx = PAPER_STEPS.findIndex((s) => s.id === activeId);
    const step = PAPER_STEPS[idx];
    const valid = builder.stepValid(activeId);
    const atLast = idx === PAPER_STEPS.length - 1;

    return (
        <div className="grid gap-4">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold">AI Paper Builder</h2>
                    <p className="text-muted-foreground text-sm">
                        16 guided steps · Marks Contract enforced live
                    </p>
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                        builder.reset();
                        setActiveId("basics");
                    }}
                >
                    ↺ Start over
                </Button>
            </div>

            <PaperBuilderStepper
                activeId={activeId}
                onSelect={setActiveId}
                isValid={builder.stepValid}
            />

            <div className="rounded-md border p-4">
                <h3 className="mb-3 text-sm font-semibold">
                    {step.stepNo}. {step.title}
                </h3>
                <StepPanel id={activeId} builder={builder} chapters={chapters} />
            </div>

            <MarksBar
                total={builder.state.basics.totalMarks}
                custom={builder.customMarks}
                ai={builder.aiMarks}
                balance={builder.balance}
                remaining={builder.aiBudget}
                perChapter={builder.coverageChecks}
            />

            <div className="modal-actions">
                <Button
                    variant="outline"
                    disabled={idx === 0}
                    onClick={() => setActiveId(PAPER_STEPS[Math.max(0, idx - 1)].id)}
                >
                    ← Back
                </Button>
                <Button
                    variant="primary"
                    disabled={atLast || !valid}
                    onClick={() =>
                        setActiveId(PAPER_STEPS[Math.min(PAPER_STEPS.length - 1, idx + 1)].id)
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
    );
}