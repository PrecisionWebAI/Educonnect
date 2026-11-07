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

// The school's students — one row per learner, with the family's contact (read from
// the guardian, who is a person of their own), the roll status (Active / Inactive)
// and the View / Logins / Action / Delete buttons.
//
// Every row here **is** a student: there is no draft to hide, so the table has no
// filter for one and the admission number is always present.

export default function StudentsTable({
    rows,
    onView,
    onAction,
    onLogins,
    onDelete,
}: {
    rows: AdmissionApplicationRow[];
    onView: (row: AdmissionApplicationRow) => void;
    onAction: (row: AdmissionApplicationRow) => void;
    /** Opens the student/guardian logins this admission created. */
    onLogins: (row: AdmissionApplicationRow) => void;
    onDelete: (row: AdmissionApplicationRow) => void;
}) {
    const columns: Column<AdmissionApplicationRow>[] = [
        {
            key: "admissionNumber",
            header: "Adm No.",
            render: (r) => r.admissionNumber || "—",
        },
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
                                : "This student has no login (the form carried no email)"
                        }
                        onClick={() => onLogins(r)}
                    >
                        Logins
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onAction(r)}>
                        Action
                    </Button>
                    <Button
                        variant="danger"
                        size="sm"
                        disabled={!r.studentId}
                        title="Permanently delete this student and their records"
                        onClick={() => onDelete(r)}
                    >
                        Delete
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
            empty="No students to show yet."
        />
    );
}
