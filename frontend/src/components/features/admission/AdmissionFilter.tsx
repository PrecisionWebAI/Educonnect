"use client";

import { Input, Select } from "@/components/ui";
import type { AdmissionFilterField } from "./admission-options";

// Admission filter — exactly two controls: which field to search and the
// value to look for (a class number, a section letter, a phone digit…).

export default function AdmissionFilter({
    fields,
    field,
    onFieldChange,
    value,
    onValueChange,
}: {
    fields: AdmissionFilterField[];
    field: string;
    onFieldChange: (field: string) => void;
    value: string;
    onValueChange: (value: string) => void;
}) {
    const active = fields.find((f) => f.value === field) ?? fields[0];

    return (
        <div className="toolbar">
            <Select value={field} onChange={(e) => onFieldChange(e.target.value)}>
                {fields.map((f) => (
                    <option key={f.value} value={f.value}>
                        {f.label}
                    </option>
                ))}
            </Select>
            <div className="toolbar-search">
                <Input
                    value={value}
                    placeholder={`Search by ${active.label.toLowerCase()}…`}
                    onChange={(e) => onValueChange(e.target.value)}
                />
            </div>
        </div>
    );
}
