"use client";

// ============================================================
// ImagesStep — blueprint §1.10 (Step 10: Images every way)
// Attach to a chosen question via the 6-way ImagePicker.
// ============================================================

import { useState } from "react";
import { Select } from "@/components/ui";
import type { PaperBuilderApi } from "../usePaperBuilder";
import ImagePicker from "../widgets/ImagePicker";

export default function ImagesStep({ builder }: { builder: PaperBuilderApi }) {
    const all = [...builder.state.customQuestions, ...builder.state.generatedQuestions];
    const [selectedId, setSelectedId] = useState<string>("");
    const selected = all.find((q) => q.id === selectedId) ?? all[0];

    return (
        <div className="grid gap-3">
            <p className="text-sm text-muted-foreground">
                Attach images to questions — photo · source diagram · AI-generated · URL · bank
                reuse · collage. Every image is stored, versioned, captioned and indexed.
            </p>
            {all.length === 0 ? (
                <p className="rounded-md border p-4 text-sm text-muted-foreground">
                    Add a custom question or generate a draft first — an image needs a question to
                    attach to.
                </p>
            ) : (
                <>
                    <Select
                        label="Pick a question to attach an image to"
                        value={selected.id}
                        onChange={(e) => setSelectedId(e.target.value)}
                    >
                        {all.map((q) => (
                            <option key={q.id} value={q.id}>
                                {q.origin === "teacher" ? "CUSTOM" : "AI"} · {q.text.slice(0, 60)}…
                            </option>
                        ))}
                    </Select>
                    <ImagePicker
                        questionId={selected.id}
                        current={selected.image}
                        onAttach={(id, image) => {
                            const q = all.find((x) => x.id === id);
                            if (q) {
                                builder.upsertQuestion({ ...q, image });
                            }
                        }}
                    />
                </>
            )}
        </div>
    );
}