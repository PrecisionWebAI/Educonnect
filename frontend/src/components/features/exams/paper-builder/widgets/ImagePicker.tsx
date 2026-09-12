"use client";

// ============================================================
// ImagePicker — blueprint §1.10: every way a question gets an
// image. Photo upload · source diagram · AI-generated · URL ·
// bank reuse · collage. Demo mode stores a caption reference.
// ============================================================

import { useState } from "react";
import { Button, Input, Select, Textarea } from "@/components/ui";
import type { ImageKind, ImageRef } from "@/types/exam-builder";

const KINDS: { value: ImageKind; label: string; hint: string }[] = [
    { value: "photo", label: "📷 Teacher photo / camera", hint: "Upload from device" },
    { value: "source", label: "📄 Source / diagram extract", hint: "Crop from a book page / PDF figure" },
    { value: "ai", label: "✨ AI-generated diagram", hint: "Generate an illustration for this question" },
    { value: "url", label: "🔗 Image URL", hint: "Fetch + store (never hot-link)" },
    { value: "bank", label: "🗂 Question-bank reuse", hint: "Pick an existing bank image" },
    { value: "collage", label: "🖼 Collage (2+ images)", hint: "Combine before/after or two diagrams" },
];

export default function ImagePicker({
    questionId,
    onAttach,
    current,
}: {
    questionId: string;
    onAttach: (id: string, image: ImageRef) => void;
    current?: ImageRef;
}) {
    const [kind, setKind] = useState<ImageKind>("photo");
    const [caption, setCaption] = useState(current?.caption ?? "");
    const [altText, setAltText] = useState(current?.altText ?? "");
    const [answerKey, setAnswerKey] = useState(current?.answerKeyImage ?? false);

    function attach() {
        onAttach(questionId, {
            kind,
            caption: caption.trim() || `${kind} image`,
            altText: altText.trim() || (caption.trim() || `${kind} image`),
            answerKeyImage: answerKey,
            questionImage: true,
            fileUrl: `demo://${kind}/${questionId}`,
        });
    }

    return (
        <div className="rounded-md border p-3">
            <p className="text-sm font-medium">Attach an image ({questionId})</p>
            <Select
                className="mt-2"
                value={kind}
                onChange={(e) => setKind(e.target.value as ImageKind)}
            >
                {KINDS.map((k) => (
                    <option key={k.value} value={k.value}>
                        {k.label} — {k.hint}
                    </option>
                ))}
            </Select>
            <Input
                className="mt-2"
                label="Caption / description"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
            />
            <Input
                className="mt-2"
                label="Alt text (accessibility)"
                hint="AI-suggested, editable"
                value={altText}
                onChange={(e) => setAltText(e.target.value)}
            />
            <Textarea
                className="mt-2"
                label="(Demo) paste/simulate the image"
                rows={2}
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
            />
            <label className="mt-2 flex items-center gap-2 text-sm">
                <input
                    type="checkbox"
                    checked={answerKey}
                    onChange={(e) => setAnswerKey(e.target.checked)}
                />
                Also produce an answer-key image (labelled/diagram answer)
            </label>
            <div className="mt-2 modal-actions">
                <Button variant="primary" size="sm" onClick={attach}>
                    Attach image
                </Button>
                {current && (
                    <span className="text-xs text-muted-foreground">
                        Current: {current.kind} ({current.caption})
                    </span>
                )}
            </div>
        </div>
    );
}