"use client";

import { Badge, Button, Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { AdmissionApplicationRow } from "@/types";
import {
    primaryEmail,
    primaryGuardian,
    primaryPhone,
    studentName,
    studentStatus,
} from "./admission-options";

// Registered students — Student, Guardian, Class, Section, contacts,
// Status (Active / Inactive) and the View / Action buttons.

export default function RegisteredStudentsTable({
    rows,
    onView,
    onAction,
    onLogins,
}: {
    rows: AdmissionApplicationRow[];
    onView: (row: AdmissionApplicationRow) => void;
    onAction: (row: AdmissionApplicationRow) => void;
    /** Opens the student/guardian logins this application created. */
    onLogins: (row: AdmissionApplicationRow) => void;
}) {
    const columns: Column<AdmissionApplicationRow>[] = [
        {
            key: "student",
            header: "Student",
            render: (r) => studentName(r) || "—",
        },
        { key: "guardian", header: "Guardian", render: primaryGuardian },
        { key: "class", header: "Class", render: (r) => r.appliedForClassLevel || "—" },
        { key: "section", header: "Section", render: (r) => r.appliedSectionPreference || "—" },
        { key: "email", header: "Email", render: primaryEmail },
        { key: "phone", header: "Phone", render: primaryPhone },
        {
            key: "status",
            header: "Status",
            render: (r) => {
                const status = studentStatus(r);
                return <Badge tone={status === "Active" ? "green" : "muted"}>{status}</Badge>;
            },
        },
        {
            key: "logins",
            header: "Logins",
            render: (r) => {
                if (!r.studentLoginEmail) {
                    return <span className="text-muted-foreground">—</span>;
                }
                return (
                    <span style={{ fontSize: "0.8rem" }}>
                        <code>{r.studentLoginEmail}</code>
                        {r.guardianLoginEmail ? (
                            <>
                                <br />
                                <code className="text-muted-foreground">
                                    {r.guardianLoginEmail}
                                </code>
                            </>
                        ) : null}
                    </span>
                );
            },
        },
        {
            key: "actions",
            header: "",
            align: "right",
            render: (r) => (
                <span style={{ display: "inline-flex", gap: "0.4rem" }}>
                    <Button variant="outline" size="sm" onClick={() => onView(r)}>
                        View
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        disabled={!r.studentLoginEmail}
                        title={
                            r.studentLoginEmail
                                ? "Show the logins, or issue a new password"
                                : "Not registered yet - logins are created on register"
                        }
                        onClick={() => onLogins(r)}
                    >
                        Logins
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onAction(r)}>
                        Action
                    </Button>
                </span>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            empty="No registered students match this filter."
        />
    );
}
