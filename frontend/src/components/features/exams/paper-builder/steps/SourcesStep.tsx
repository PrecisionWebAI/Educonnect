"use client";

// ============================================================
// SourcesStep — blueprint §1.2 (Step 2: Sources Types A–G)
// ============================================================

import { Button, Select } from "@/components/ui";
import type { SourceItem } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";

const SOURCE_TYPES: SourceItem["sourceType"][] = ["A", "B", "C", "D", "E", "F", "G"];
const SOURCE_LABELS: Record<SourceItem["sourceType"], string> = {
    A: "Upload PDF",
    B: "Upload image(s)",
    C: "Website / URL",
    D: "Paste text",
    E: "Question bank",
    F: "Multiple sources",
    G: "Content Library reuse",
};

export default function SourcesStep({ builder }: { builder: PaperBuilderApi }) {
    function addSource(t: SourceItem["sourceType"]) {
        builder.addSource({
            id: `src${Date.now().toString()}`,
            sourceType: t,
            label: `${t} — ${SOURCE_LABELS[t]}`,
            kind: "knowledge",
            strictness: "Strict",
            chapters: builder.state.basics.chapters,
        });
    }

    return (
        <div className="grid gap-3">
            <div className="flex flex-wrap gap-1">
                {SOURCE_TYPES.map((t) => (
                    <Button key={t} variant="outline" size="sm" onClick={() => addSource(t)}>
                        + Type {t}
                    </Button>
                ))}
            </div>
            <p className="text-sm text-muted-foreground">
                A upload PDF · B upload image(s) · C website/URL · D paste text · E question bank
                · F multiple sources · G reuse Content Library (saved, vector-indexed — no
                re-upload).
            </p>
            {builder.state.sources.length === 0 ? (
                <p className="text-sm text-muted-foreground">Add at least one source to continue.</p>
            ) : (
                <div className="grid gap-2">
                    {builder.state.sources.map((s) => (
                        <div key={s.id} className="flex items-center gap-2 rounded border p-2">
                            <span className="text-sm font-medium">{s.label}</span>
                            <Select
                                value={s.strictness}
                                onChange={(e) => {
                                    builder.removeSource(s.id);
                                    builder.addSource({
                                        ...s,
                                        strictness: e.target.value as SourceItem["strictness"],
                                    });
                                }}
                            >
                                <option>Strict</option>
                                <option>Flexible</option>
                                <option>Creative</option>
                            </Select>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => builder.removeSource(s.id)}
                            >
                                ✕
                            </Button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}