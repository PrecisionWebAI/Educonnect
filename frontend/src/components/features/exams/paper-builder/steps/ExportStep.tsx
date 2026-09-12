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
    { value: "both", label: "Paper + answer key" },
];

export default function ExportStep({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const [variant, setVariant] = useState("both");
    const [format, setFormat] = useState("pdf");

    function doExport() {
        const name = `${builder.state.basics.title || "paper"}.${format}`;
        push("success", `Export queued (demo): ${name} — ${variant}`);
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
            </div>
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