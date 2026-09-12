"use client";

// ============================================================
// InstructionsStep — blueprint §1.11 (Step 11)
// Structured quick-chip instructions + free text.
// ============================================================

import { useState } from "react";
import { Button, Input } from "@/components/ui";
import type { PaperBuilderApi } from "../usePaperBuilder";

const CHIPS = [
    "No question should require knowledge outside the uploaded source.",
    "Use simple English.",
    "Do not ask about examples marked optional.",
    "Create 2 questions from the diagram in the image.",
];

export default function InstructionsStep({ builder }: { builder: PaperBuilderApi }) {
    const [draft, setDraft] = useState("");

    return (
        <div className="grid gap-3">
            <p className="text-sm text-muted-foreground">
                Add special instructions for the generator. These are stored and shown on the
                review screen.
            </p>
            <div className="flex flex-wrap gap-1">
                {CHIPS.map((chip) => (
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
                        + {chip.slice(0, 40)}…
                    </Button>
                ))}
            </div>
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

            {builder.state.instructions.length > 0 && (
                <ul className="grid gap-1">
                    {builder.state.instructions.map((ins, i) => (
                        <li key={i} className="flex items-center justify-between rounded border p-2 text-sm">
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
    );
}