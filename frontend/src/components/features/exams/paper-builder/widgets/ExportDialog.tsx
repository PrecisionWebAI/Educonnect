"use client";

// ============================================================
// ExportDialog — the download options, opened from the Generate step.
//
// Export used to be its own wizard step; it is now a popup behind one button,
// because there is nothing to fill in on a page — the teacher picks a format
// and downloads.
//
// NOTE: the backend has no export endpoint yet, so "Download" confirms the
// chosen options instead of streaming a file. The options here are exactly the
// ones such an endpoint needs (what to export, format, versions, language), so
// wiring it up later is a one-line change.
// ============================================================

import { useState } from "react";
import { Button, Modal, Select } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import type { PaperBuilderApi } from "../usePaperBuilder";

const VARIANTS = [
    { value: "paper", label: "Student paper only" },
    { value: "key", label: "Answer key only" },
    { value: "scheme", label: "Marking scheme (rubrics)" },
    { value: "both", label: "Paper + answer key" },
    { value: "all", label: "Paper + key + marking scheme" },
];

const FORMATS = [
    { value: "pdf", label: "PDF (print-ready)" },
    { value: "docx", label: "DOCX (editable)" },
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <label className="flex min-w-0 flex-col gap-1">
            <span className="text-muted-foreground text-xs font-medium">{label}</span>
            {children}
        </label>
    );
}

export default function ExportDialog({
    open,
    onClose,
    builder,
}: {
    open: boolean;
    onClose: () => void;
    builder: PaperBuilderApi;
}) {
    const { push } = useToast();
    const [variant, setVariant] = useState("both");
    const [format, setFormat] = useState("pdf");
    const [version, setVersion] = useState("A");
    const [language, setLanguage] = useState("en");

    function download() {
        const name = `${builder.state.basics.title || "paper"}-v${version}.${format}`;
        const extra = language === "bilingual" ? " · bilingual" : "";
        push("success", `Export queued (demo): ${name} — ${variant}${extra}`);
        onClose();
    }

    return (
        <Modal open={open} title="Export paper" onClose={onClose}>
            <div className="form-grid">
                <Field label="What to export">
                    <Select value={variant} onChange={(e) => setVariant(e.target.value)}>
                        {VARIANTS.map((v) => (
                            <option key={v.value} value={v.value}>
                                {v.label}
                            </option>
                        ))}
                    </Select>
                </Field>
                <Field label="Format">
                    <Select value={format} onChange={(e) => setFormat(e.target.value)}>
                        {FORMATS.map((f) => (
                            <option key={f.value} value={f.value}>
                                {f.label}
                            </option>
                        ))}
                    </Select>
                </Field>
                <Field label="Exam versions">
                    <Select value={version} onChange={(e) => setVersion(e.target.value)}>
                        {VERSIONS.map((v) => (
                            <option key={v.value} value={v.value}>
                                {v.label}
                            </option>
                        ))}
                    </Select>
                </Field>
                <Field label="Language">
                    <Select value={language} onChange={(e) => setLanguage(e.target.value)}>
                        {LANGUAGES.map((l) => (
                            <option key={l.value} value={l.value}>
                                {l.label}
                            </option>
                        ))}
                    </Select>
                </Field>
            </div>

            {!builder.balanced && (
                <p className="mt-3 text-sm text-amber-700">
                    Balance the Marks Contract to enable export.
                </p>
            )}

            <div className="modal-actions">
                <Button variant="ghost" onClick={onClose}>
                    Cancel
                </Button>
                <Button variant="primary" disabled={!builder.balanced} onClick={download}>
                    Download {format.toUpperCase()}
                </Button>
            </div>
        </Modal>
    );
}
