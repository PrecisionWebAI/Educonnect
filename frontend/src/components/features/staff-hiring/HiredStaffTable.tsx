"use client";

import { Badge, Button, Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import { staffRoleLabel } from "@/services";
import type { StaffProfileRow } from "@/types";

// The Hired tab: the staff the school actually has - one row per `employee` row,
// carrying the login and the employee code the registration created.
//
// Four actions per row, in the order the office needs them:
//
//   * View       the read-only popup (Edit lives inside it) - the whole person on one
//                screen before anything is changed
//   * Logins     reopens the credentials panel (a password is never stored in the
//                clear, so that panel offers Reset)
//   * Deactivate the staff side switched off: roles withdrawn, the day stamped, every
//                record left in place. Their login stays if it still opens something
//                else - a teacher who is also a parent keeps signing in. Someone
//                already off the roll shows **Reactivate** here instead.
//   * Delete     only for a record the school never really had; anything with history
//                behind it is refused by the server (409) and told to deactivate.
//
// A person who left is **not** deleted, so they stay on this list with their badge -
// the salary register and last term's timetable still point at them.

/** The badge for a row that is no longer on the staff roll. */
function leftOnLabel(row: StaffProfileRow): string {
    if (!row.leftOn) return "Left";
    const when = new Date(row.leftOn);
    if (Number.isNaN(when.getTime())) return "Left";
    return `Left \u00b7 ${when.toLocaleDateString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
    })}`;
}

export default function HiredStaffTable({
    rows,
    onView,
    onShowLogins,
    onLifecycle,
    onDelete,
}: {
    rows: StaffProfileRow[];
    onView: (row: StaffProfileRow) => void;
    onShowLogins: (row: StaffProfileRow) => void;
    /** Opens the popup on its lifecycle panel (Deactivate / Reactivate). */
    onLifecycle: (row: StaffProfileRow) => void;
    onDelete: (row: StaffProfileRow) => void;
}) {
    const columns: Column<StaffProfileRow>[] = [
        {
            key: "employeeCode",
            header: "Employee ID",
            render: (r) => <b>{r.employeeCode}</b>,
        },
        { key: "fullName", header: "Name" },
        {
            key: "roleCodenames",
            header: "Role",
            render: (r) =>
                (r.roleCodenames.length > 0 ? r.roleCodenames : [r.roleCodename])
                    .map(staffRoleLabel)
                    .join(", "),
        },
        { key: "department", header: "Department" },
        {
            key: "phone",
            header: "Phone",
            render: (r) => r.phone || "—",
        },
        {
            key: "salaryMonthly",
            header: "Salary",
            render: (r) =>
                r.salaryMonthly != null ? `₹${r.salaryMonthly.toLocaleString()}` : "—",
        },
        {
            key: "email",
            header: "Login",
            render: (r) => <code className="text-xs break-all">{r.email}</code>,
        },
        { key: "joiningDate", header: "Joined" },
        {
            key: "isActive",
            header: "Status",
            render: (r) =>
                r.isActive ? (
                    <Badge tone="green">Active</Badge>
                ) : (
                    <span
                        title={`${r.deactivatedRoles.join(", ") || "Staff"} access withdrawn`}
                    >
                        <Badge tone="amber">{leftOnLabel(r)}</Badge>
                    </span>
                ),
        },
        {
            key: "actions",
            header: "",
            align: "right",
            render: (r) => (
                <div className="flex gap-1">
                    <Button size="sm" variant="outline" onClick={() => onView(r)}>
                        View
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => onShowLogins(r)}>
                        Logins
                    </Button>
                    {r.isActive ? (
                        <Button size="sm" variant="danger" onClick={() => onLifecycle(r)}>
                            Deactivate
                        </Button>
                    ) : (
                        <Button size="sm" variant="primary" onClick={() => onLifecycle(r)}>
                            Reactivate
                        </Button>
                    )}
                    <Button size="sm" variant="danger" onClick={() => onDelete(r)}>
                        Delete
                    </Button>
                </div>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            empty="No staff hired yet - register a hire on the Registration tab."
        />
    );
}
