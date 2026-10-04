"use client";

import { Input, Select } from "@/components/ui";
import type { AdmissionStudentStatus, SeparationSession } from "@/types";
import { REGISTERED_FILTER_FIELDS, SEPARATION_SESSION_OPTIONS } from "./admission-options";

// Registered-tab filters: the generic field + value pair, plus the
// separation controls — status (Active / Inactive), reason and
// completed / incomplete session.

const STATUS_OPTIONS: (AdmissionStudentStatus | "All")[] = ["All", "Active", "Inactive"];

export default function RegisteredFilters({
    field,
    onFieldChange,
    value,
    onValueChange,
    status,
    onStatusChange,
    reason,
    onReasonChange,
    session,
    onSessionChange,
}: {
    field: string;
    onFieldChange: (field: string) => void;
    value: string;
    onValueChange: (value: string) => void;
    status: AdmissionStudentStatus | "All";
    onStatusChange: (status: AdmissionStudentStatus | "All") => void;
    reason: string;
    onReasonChange: (reason: string) => void;
    session: SeparationSession | "All";
    onSessionChange: (session: SeparationSession | "All") => void;
}) {
    const active = REGISTERED_FILTER_FIELDS.find((f) => f.value === field) ?? REGISTERED_FILTER_FIELDS[0];

    return (
        <div className="toolbar">
            <Select value={field} onChange={(e) => onFieldChange(e.target.value)}>
                {REGISTERED_FILTER_FIELDS.map((f) => (
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
            <Select
                value={status}
                onChange={(e) => onStatusChange(e.target.value as AdmissionStudentStatus | "All")}
            >
                {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                        {s === "All" ? "All Status" : s}
                    </option>
                ))}
            </Select>
            <Input
                value={reason}
                placeholder="Reason (e.g. Rusticated)"
                onChange={(e) => onReasonChange(e.target.value)}
            />
            <Select
                value={session}
                onChange={(e) => onSessionChange(e.target.value as SeparationSession | "All")}
            >
                <option value="All">All Sessions</option>
                {SEPARATION_SESSION_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                        {s}
                    </option>
                ))}
            </Select>
        </div>
    );
}
