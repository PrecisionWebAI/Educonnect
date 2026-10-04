"use client";

import type { ReactNode } from "react";
import { Card, Input, Select, Textarea } from "@/components/ui";
import type { AdmissionFormValues } from "@/types";
import { FORM_SECTIONS, type AdmissionFieldDef } from "./admission-options";

// The admission form — every field of `admissionapplication`, grouped by
// section. The same component renders the read-only view (`readOnly`).
// No field is mandatory at this stage.
//
// Layout note: an explicit Tailwind grid with row gaps is used because the
// shared `.form-grid` class has `gap: 0 1rem` (no row gap), which makes each
// field label collide with the input above it once there are many rows.
// `columns="single"` is used inside the narrow read-only popup.

function gridClass(columns: "two" | "single") {
    return columns === "single"
        ? "grid grid-cols-1 gap-y-4"
        : "grid grid-cols-1 gap-x-4 gap-y-5 md:grid-cols-2";
}

function FieldShell({
    wide,
    columns,
    children,
}: {
    wide?: boolean;
    columns: "two" | "single";
    children: ReactNode;
}) {
    return (
        <div className={wide && columns === "two" ? "md:col-span-2" : undefined}>{children}</div>
    );
}

function ReadOnlyField({ field, value }: { field: AdmissionFieldDef; value: string }) {
    return (
        <div className="space-y-1.5">
            <span className="text-muted-foreground block text-xs font-medium">{field.label}</span>
            <p className={value ? "text-sm break-words" : "text-muted-foreground text-sm"}>
                {value || "—"}
            </p>
        </div>
    );
}

export default function AdmissionForm({
    value,
    onChange,
    readOnly = false,
    columns = "two",
}: {
    value: AdmissionFormValues;
    onChange?: (values: AdmissionFormValues) => void;
    readOnly?: boolean;
    columns?: "two" | "single";
}) {
    const update = (key: keyof AdmissionFormValues, next: string) => {
        if (!onChange) return;
        // Current/Last Class follows the Admission Class until the user
        // changes it explicitly (then it stays independent).
        if (key === "appliedForClassLevel") {
            const keepInSync =
                !value.currentClassOrLastClass ||
                value.currentClassOrLastClass === value.appliedForClassLevel;
            onChange({
                ...value,
                appliedForClassLevel: next,
                ...(keepInSync ? { currentClassOrLastClass: next } : {}),
            });
            return;
        }
        onChange({ ...value, [key]: next });
    };

    return (
        <div>
            {FORM_SECTIONS.map((section) => (
                <Card key={section.title} title={section.title} className="mb-5">
                    <div className={gridClass(columns)}>
                        {section.fields.map((field) => {
                            const current = value[field.key];
                            const wide = field.type === "textarea";

                            if (readOnly) {
                                return (
                                    <FieldShell key={field.key} wide={wide} columns={columns}>
                                        <ReadOnlyField field={field} value={current} />
                                    </FieldShell>
                                );
                            }

                            if (field.options) {
                                return (
                                    <FieldShell key={field.key} wide={wide} columns={columns}>
                                        <Select
                                            label={field.label}
                                            value={current}
                                            onChange={(e) => update(field.key, e.target.value)}
                                        >
                                            <option value="">Select…</option>
                                            {field.options.map((option) => (
                                                <option key={option} value={option}>
                                                    {option}
                                                </option>
                                            ))}
                                        </Select>
                                    </FieldShell>
                                );
                            }

                            if (field.type === "textarea") {
                                return (
                                    <FieldShell key={field.key} wide columns={columns}>
                                        <Textarea
                                            label={field.label}
                                            rows={2}
                                            value={current}
                                            onChange={(e) => update(field.key, e.target.value)}
                                        />
                                    </FieldShell>
                                );
                            }

                            return (
                                <FieldShell key={field.key} wide={wide} columns={columns}>
                                    <Input
                                        label={field.label}
                                        type={field.type ?? "text"}
                                        value={current}
                                        onChange={(e) => update(field.key, e.target.value)}
                                    />
                                </FieldShell>
                            );
                        })}
                    </div>
                </Card>
            ))}
        </div>
    );
}
