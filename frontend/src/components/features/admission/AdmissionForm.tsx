"use client";

import { type ReactNode } from "react";
import { Card, Input, Select, Textarea } from "@/components/ui";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import type { AdmissionFormValues } from "@/types";
import { ADMISSION_FORM_SECTIONS, type AdmissionFieldDef } from "./admission-options";

// The admission form — every field of `admissionapplication`, grouped by
// section. The same component renders the read-only view (`readOnly`).
//
// The fields the form cannot be registered without carry a `*` (`required` on the
// field definition) and are checked by `missingRequiredFields` before the Register
// button opens its confirmation — the server enforces the same rule, so a draft
// can stay partial but a registration cannot.
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

/** The label a field shows — mandatory fields are marked with a `*`. */
function fieldLabel(field: AdmissionFieldDef): string {
    return field.required ? `${field.label} *` : field.label;
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
    // Class and Section read the **platform catalog** - the `classname` and
    // `section` rows - so the office picks from what the database offers, and the
    // picked ids travel with the form. The static lists in `admission-options.ts`
    // are the fallback while the catalog loads (and for the filter dropdowns).
    const { classes, classNames, sectionsOf } = useClassCatalog();

    const optionsFor = (field: AdmissionFieldDef): readonly string[] => {
        if (field.key === "appliedForClassLevel" && classNames.length) {
            return classNames;
        }
        if (field.key === "appliedSectionPreference") {
            const sections = sectionsOf(value.appliedForClassLevel).map((item) => item.name);
            if (sections.length) return sections;
        }
        return field.options ?? [];
    };

    const update = (key: keyof AdmissionFormValues, next: string) => {
        if (!onChange) return;
        // Class and Section carry their catalog ids, so the server places the
        // student in exactly the class-section the office picked rather than
        // re-reading a name.
        if (key === "appliedForClassLevel") {
            const keepInSync =
                !value.currentClassOrLastClass ||
                value.currentClassOrLastClass === value.appliedForClassLevel;
            const sections = sectionsOf(next);
            const keepsSection = sections.some(
                (item) => item.name === value.appliedSectionPreference,
            );
            onChange({
                ...value,
                appliedForClassLevel: next,
                appliedClassId: classes.find((item) => item.name === next)?.id ?? "",
                // A section the new class does not run is cleared rather than
                // silently kept.
                ...(keepsSection ? {} : { appliedSectionPreference: "", appliedSectionId: "" }),
                ...(keepInSync ? { currentClassOrLastClass: next } : {}),
            });
            return;
        }
        if (key === "appliedSectionPreference") {
            onChange({
                ...value,
                appliedSectionPreference: next,
                appliedSectionId:
                    sectionsOf(value.appliedForClassLevel).find((item) => item.name === next)?.id ??
                    "",
            });
            return;
        }
        onChange({ ...value, [key]: next });
    };

    return (
        <div>
            {ADMISSION_FORM_SECTIONS.map((section) => (
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
                                            label={fieldLabel(field)}
                                            value={current}
                                            onChange={(e) => update(field.key, e.target.value)}
                                        >
                                            <option value="">Select…</option>
                                            {optionsFor(field).map((option) => (
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
                                            label={fieldLabel(field)}
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
                                        label={fieldLabel(field)}
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
