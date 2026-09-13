"use client";

// ============================================================
// ExportStep — blueprint §1.16 (Step 16)
// Export variants: student paper / answer key / both, as PDF
// or DOCX. Demo mode toasts until the export endpoint ships.
// ============================================================

import { useState } from "react";
import { Button, Select } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import type { PaperBuilderApi } from "../usePaperBuilder";

const VARIANTS = [
    { value: "paper", label: "Student paper only" },
    { value: "key", label: "Answer key only" },
    { value: "scheme", label: "Marking scheme (rubrics)" },
    { value: "both", label: "Paper + answer key" },
    { value: "all", label: "Paper + key + marking scheme" },
];

const VERSIONS = [
    { value: "A", label: "Paper A (single version)" },
    { value: "B", label: "Paper A + B (anti-copying)" },
    { value: "C", label: "Paper A + B + C (full shuffle)" },
];

const LANGUAGES = [
    { value: "en", label: "English only" },
    { value: "hi", label: "Hindi only" },
    { value: "bilingual", label: "Bilingual (Hindi + English)" },
];

export default function ExportStep({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const [variant, setVariant] = useState("both");
    const [format, setFormat] = useState("pdf");
    const [version, setVersion] = useState("A");
    const [language, setLanguage] = useState("en");

    function doExport() {
        const name = `${builder.state.basics.title || "paper"}-v${version}.${format}`;
        const extra = language === "bilingual" ? " · bilingual" : "";
        push("success", `Export queued (demo): ${name} — ${variant}${extra}`);
    }

    return (
        <div className="grid gap-3">
            <div className="grid gap-3 rounded-md border p-4 md:grid-cols-2">
                <Select label="What to export" value={variant} onChange={(e) => setVariant(e.target.value)}>
                    {VARIANTS.map((v) => (
                        <option key={v.value} value={v.value}>
                            {v.label}
                        </option>
                    ))}
                </Select>
                <Select label="Format" value={format} onChange={(e) => setFormat(e.target.value)}>
                    <option value="pdf">PDF (print-ready)</option>
                    <option value="docx">DOCX (editable)</option>
                </Select>
                <Select label="Exam versions" value={version} onChange={(e) => setVersion(e.target.value)}>
                    {VERSIONS.map((v) => (
                        <option key={v.value} value={v.value}>
                            {v.label}
                        </option>
                    ))}
                </Select>
                <Select label="Language" value={language} onChange={(e) => setLanguage(e.target.value)}>
                    {LANGUAGES.map((l) => (
                        <option key={l.value} value={l.value}>
                            {l.label}
                        </option>
                    ))}
                </Select>
            </div>
            <p className="text-muted-foreground text-xs">
                Versions A/B/C share the same blueprint but shuffle question order/content so
                neighbouring students can't copy. The marking scheme carries per-question rubrics
                ("Definition 1m · Role of sunlight 1m …"). The answer key includes point breakdowns.
            </p>
            <div className="modal-actions">
                <Button
                    variant="primary"
                    disabled={!builder.balanced}
                    onClick={doExport}
                >
                    ⬇ Export {format.toUpperCase()}
                </Button>
                {!builder.balanced && (
                    <span className="text-sm text-amber-700">
                        Balance the Marks Contract to enable export.
                    </span>
                )}
            </div>
            <p className="text-muted-foreground text-xs">
                Exports are stored, versioned and re-downloadable from the Papers view. Demo mode
                simulates the file until the backend export endpoint is wired.
            </p>
        </div>
    );
}