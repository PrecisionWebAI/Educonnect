"use client";

// ============================================================
// InstructionsStep — blueprint §1.8 + §1.11 merged (Step 8:
// Instructions & Rules). Constraints toggles sit next to the
// generator's special instructions, scaffolded with recommended
// quick-chip options ("Use simple English", …) + free text.
// ============================================================

import { useState } from "react";
import { Button, Input } from "@/components/ui";
import type { PaperBuilderApi } from "../usePaperBuilder";

/** Recommended one-click instruction chips (blueprint §1.11). */
const RECOMMENDED = [
    "Use simple English.",
    "Base every question only on the uploaded sources.",
    "No question should require knowledge outside the uploaded source.",
    "Create at least one question from the diagram in the image.",
    "Do not ask about examples marked optional.",
];

export default function InstructionsStep({ builder }: { builder: PaperBuilderApi }) {
    const [draft, setDraft] = useState("");
    const c = builder.state.constraints;

    const toggles: {
        key: "noDuplicates" | "noAnswerLeak" | "sourceOnly" | "avoidReuse";
        label: string;
    }[] = [
        { key: "noDuplicates", label: "No duplicate / near-duplicate questions" },
        { key: "noAnswerLeak", label: "No cross-answer leakage" },
        { key: "sourceOnly", label: "Source-only answers (Strict)" },
        { key: "avoidReuse", label: "Avoid questions used in previous papers" },
    ];

    return (
        <div className="grid gap-3">
            {/* Rules — merged from the old Constraints step */}
            <div className="rounded-md border p-3">
                <p className="text-sm font-medium">Rules (constraints)</p>
                <p className="mt-1 text-xs text-muted-foreground">
                    Quality guardrails the generator must respect.
                </p>
                <div className="mt-2 grid gap-1">
                    {toggles.map(({ key, label }) => (
                        <label key={key} className="flex items-center gap-2 text-sm">
                            <input
                                type="checkbox"
                                checked={Boolean(c[key])}
                                onChange={(e) => builder.setConstraints({ [key]: e.target.checked })}
                            />
                            {label}
                        </label>
                    ))}
                </div>
                <div className="mt-2 grid gap-3 sm:grid-cols-2">
                    <Input
                        label="Min application questions"
                        type="number"
                        min={0}
                        value={String(c.minApplication)}
                        onChange={(e) =>
                            builder.setConstraints({ minApplication: Number(e.target.value) })
                        }
                    />
                    <Input
                        label="Min diagram questions"
                        type="number"
                        min={0}
                        value={String(c.minDiagram)}
                        onChange={(e) =>
                            builder.setConstraints({ minDiagram: Number(e.target.value) })
                        }
                    />
                </div>
            </div>

            {/* Instructions — recommended chips + custom instruction */}
            <div className="rounded-md border p-3">
                <p className="text-sm font-medium">Instructions for the generator</p>
                <p className="mt-1 text-xs text-muted-foreground">
                    Stored and shown on the review screen so you can audit what the generator was
                    told. Tap a recommended chip or add your own.
                </p>
                <p className="mt-2 text-xs font-medium text-muted-foreground">Recommended</p>
                <div className="mt-1 flex flex-wrap gap-1">
                    {RECOMMENDED.map((chip) => (
                        <Button
                            key={chip}
                            variant="outline"
                            size="sm"
                            onClick={() => {
                                if (!builder.state.instructions.includes(chip)) {
                                    builder.setInstructions([...builder.state.instructions, chip]);
                                }
                            }}
                        >
                            + {chip.slice(0, 42)}…
                        </Button>
                    ))}
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
                    <Input
                        label="Custom instruction"
                        placeholder="Type an instruction and press Add"
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                    />
                    <Button
                        variant="primary"
                        size="sm"
                        disabled={!draft.trim()}
                        onClick={() => {
                            builder.setInstructions([...builder.state.instructions, draft.trim()]);
                            setDraft("");
                        }}
                    >
                        Add instruction
                    </Button>
                </div>

                {builder.state.instructions.length > 0 && (
                    <ul className="mt-2 grid gap-1">
                        {builder.state.instructions.map((ins, i) => (
                            <li
                                key={i}
                                className="flex items-center justify-between rounded border p-2 text-sm"
                            >
                                <span>{ins}</span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() =>
                                        builder.setInstructions(
                                            builder.state.instructions.filter((_, j) => j !== i),
                                        )
                                    }
                                >
                                    ✕
                                </Button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}