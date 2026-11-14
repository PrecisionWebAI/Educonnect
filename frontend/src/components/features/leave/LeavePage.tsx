"use client";
import { useMemo, useState } from "react";
import {
    PageHeader,
    Tabs,
    Spinner,
    Card,
    Select,
    Textarea,
    Button,
    Table,
    Badge,
    type BadgeTone,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { DatePicker } from "@/components/ui/date-picker";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, ACADEMIC_STAFF_ROLES, LEADERSHIP_ROLES } from "@/lib/auth/rbac";
import { getStaffLeaves, applyLeave, getStudents } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { errorMessage } from "@/lib/api/client";
import { useLeave, type LeaveTab } from "./useLeave";
import type { LeaveApplicationItem, StaffLeaveItem } from "@/types";

const typeTone: Record<string, BadgeTone> = {
    Medical: "teal",
    Personal: "amber",
    OD: "violet",
    Event: "accent",
    Travel: "green",
    Sick: "teal",
    Casual: "amber",
    Earned: "green",
};

export default function LeavePage() {
    const l = useLeave();
    const { user } = useAuth();
    const { push } = useToast();

    const canApprove = hasAnyRole(user?.roles, [...ACADEMIC_STAFF_ROLES, ...LEADERSHIP_ROLES]);
    const canViewStaffLeave = hasAnyRole(user?.roles, LEADERSHIP_ROLES);

    const allowedTabs = useMemo(() => {
        const tabs: LeaveTab[] = ["Apply", "My Leaves"];
        if (canApprove) tabs.push("Approvals");
        if (canViewStaffLeave) tabs.push("Staff Leave");
        return tabs;
    }, [canApprove, canViewStaffLeave]);

    const activeTab = allowedTabs.includes(l.tab) ? l.tab : allowedTabs[0];

    const staffLeavesQuery = useApiQuery(["leave", "staff-requests"], getStaffLeaves, {
        enabled: canViewStaffLeave,
    });
    const staffLeaves = staffLeavesQuery.data ?? [];

    // The real students, so "Apply" files for a row that exists: the form used to
    // hard-code "Aarav Mehta" and print a success with nothing behind it.
    const canApply = hasAnyRole(user?.roles, [...ACADEMIC_STAFF_ROLES, ...LEADERSHIP_ROLES]);
    const studentsQuery = useApiQuery(["students", "leave-picker"], () => getStudents(0, 200), {
        enabled: canApply,
    });
    const students = studentsQuery.data ?? [];

    const [studentId, setStudentId] = useState("");
    const [type, setType] = useState<LeaveApplicationItem["type"]>("Medical");
    const [from, setFrom] = useState("");
    const [to, setTo] = useState("");
    const [reason, setReason] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [applyError, setApplyError] = useState<unknown>(null);

    const submit = async () => {
        if (!studentId) {
            push("error", "Choose the student whose leave this is.");
            return;
        }
        if (!from || !to) {
            push("error", "Select dates for the leave range.");
            return;
        }
        setSubmitting(true);
        setApplyError(null);
        try {
            const result = await applyLeave({
                studentId,
                leaveType: type,
                fromDate: from,
                toDate: to,
                reason: reason.trim() || undefined,
            });
            push("success", `Leave filed for ${result.person} (${result.days} day(s)).`);
            setFrom("");
            setTo("");
            setReason("");
        } catch (problem) {
            setApplyError(problem);
        } finally {
            setSubmitting(false);
        }
    };

    const cols = [
        { key: "student", header: "Student" },
        {
            key: "type",
            header: "Type",
            render: (r: LeaveApplicationItem) => (
                <Badge tone={typeTone[r.type] ?? "muted"}>{r.type}</Badge>
            ),
        },
        {
            key: "range",
            header: "Range",
            render: (r: LeaveApplicationItem) => `${r.fromDate} → ${r.toDate}`,
        },
        { key: "days", header: "Days" },
        { key: "reason", header: "Reason" },
        {
            key: "status",
            header: "Status",
            render: (r: LeaveApplicationItem) => (
                <Badge
                    tone={
                        r.status === "Approved"
                            ? "green"
                            : r.status === "Rejected"
                              ? "red"
                              : "amber"
                    }
                >
                    {r.status}
                </Badge>
            ),
        },
    ];

    const rows =
        activeTab === "My Leaves"
            ? l.leaves.filter((r) => r.status !== "Pending")
            : activeTab === "Approvals"
              ? l.leaves.filter((r) => r.status === "Pending")
              : l.leaves;
    const title =
        activeTab === "My Leaves"
            ? "Leave History"
            : activeTab === "Approvals"
              ? "Pending Approvals"
              : "Recent Applications";

    return (
        <div>
            <PageHeader
                title="Leave & Applications"
                subtitle="Apply for leave, track status and approve student applications."
            />

            {l.loading ? (
                <Spinner />
            ) : (
                <>
                    <div className="stat-tiles">
                        <div className="stat-tile">
                            <b>{l.leaves.length}</b>
                            <span>Applications</span>
                        </div>
                        <div className="stat-tile">
                            <b>{l.pendingCount}</b>
                            <span>Pending</span>
                        </div>
                        <div className="stat-tile">
                            <b>{l.approvedCount}</b>
                            <span>Approved</span>
                        </div>
                    </div>

                    <Tabs
                        tabs={allowedTabs}
                        active={activeTab}
                        onChange={(t) => l.setTab(t as LeaveTab)}
                    />

                    {activeTab === "Apply" && (
                        <Card title="New Leave Application">
                            <div className="form-grid">
                                <Select
                                    label="Student"
                                    value={studentId}
                                    onChange={(e) => setStudentId(e.target.value)}
                                >
                                    <option value="">Choose a student</option>
                                    {students.map((person) => (
                                        <option key={person.id} value={person.id}>
                                            {person.name} ({person.className || person.admissionNo})
                                        </option>
                                    ))}
                                </Select>
                                <Select
                                    label="Type"
                                    value={type}
                                    onChange={(e) =>
                                        setType(e.target.value as LeaveApplicationItem["type"])
                                    }
                                >
                                    {["Medical", "Personal", "OD", "Event", "Travel"].map((t) => (
                                        <option key={t}>{t}</option>
                                    ))}
                                </Select>
                                <DatePicker label="From" value={from} onChange={setFrom} />
                                <DatePicker label="To" value={to} onChange={setTo} />
                                <div style={{ gridColumn: "1 / -1" }}>
                                    <Textarea
                                        label="Reason"
                                        value={reason}
                                        onChange={(e) => setReason(e.target.value)}
                                        placeholder="Why the leave is requested..."
                                    />
                                </div>
                            </div>
                            <div className="modal-actions">
                                <Button
                                    variant="primary"
                                    loading={submitting}
                                    disabled={students.length === 0}
                                    onClick={() => void submit()}
                                >
                                    Submit Application
                                </Button>
                            </div>
                            {applyError !== null && (
                                <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                                    {errorMessage(applyError, "The application was not filed.")}
                                </p>
                            )}
                        </Card>
                    )}

                    {(activeTab === "My Leaves" || (activeTab === "Approvals" && canApprove)) && (
                        <>
                            <div
                                style={{
                                    marginBottom: "0.7rem",
                                    fontSize: "0.9rem",
                                    fontWeight: 700,
                                }}
                            >
                                {title}
                            </div>
                            {activeTab === "Approvals" && canApprove && (
                                <div style={{ marginBottom: "0.7rem" }}>
                                    {rows.map((r) =>
                                        r.status === "Pending" ? (
                                            <div
                                                key={r.id}
                                                className="row-flex"
                                                style={{ marginBottom: "0.5rem" }}
                                            >
                                                <span style={{ fontSize: "0.88rem" }}>
                                                    {r.student} - {r.type} ({r.fromDate})
                                                </span>
                                                <div className="flex gap-1">
                                                    <Button
                                                        size="sm"
                                                        variant="success"
                                                        loading={l.busy === `approve-${r.id}`}
                                                        onClick={async () => {
                                                            const done = await l.approve(r.id);
                                                            if (done) {
                                                                push("success", "Approved");
                                                            }
                                                        }}
                                                    >
                                                        Approve
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="danger"
                                                        loading={l.busy === `reject-${r.id}`}
                                                        onClick={async () => {
                                                            const done = await l.reject(r.id);
                                                            if (done) {
                                                                push("success", "Rejected");
                                                            }
                                                        }}
                                                    >
                                                        Reject
                                                    </Button>
                                                </div>
                                            </div>
                                        ) : null,
                                    )}
                                    {l.error !== null && (
                                        <p
                                            className="text-sm"
                                            style={{ color: "var(--danger, #b42318)" }}
                                        >
                                            {errorMessage(l.error, "The decision was not saved.")}
                                        </p>
                                    )}
                                </div>
                            )}
                            <Table
                                columns={cols}
                                rows={rows}
                                rowKey={(r) => r.id}
                                empty="No leave applications."
                            />
                        </>
                    )}

                    {activeTab === "Staff Leave" && canViewStaffLeave && (
                        <>
                            <p style={{ color: "var(--muted)", marginBottom: "0.6rem" }}>
                                Teacher & staff leave requests � principal approves long leaves;
                                balances shown per person.
                            </p>
                            <Table
                                columns={[
                                    {
                                        key: "staffName",
                                        header: "Staff",
                                        render: (r: StaffLeaveItem) => (
                                            <div style={{ lineHeight: 1.2 }}>
                                                <b>{r.staffName || "—"}</b>
                                                <div
                                                    style={{
                                                        color: "var(--muted)",
                                                        fontSize: "0.74rem",
                                                    }}
                                                >
                                                    {r.staffCode}
                                                </div>
                                            </div>
                                        ),
                                    },
                                    { key: "role", header: "Role" },
                                    { key: "leaveType", header: "Leave type" },
                                    { key: "fromDate", header: "From" },
                                    { key: "toDate", header: "To" },
                                    { key: "days", header: "Days" },
                                    {
                                        key: "balance",
                                        header: "Balance",
                                        render: (r: StaffLeaveItem) => r.balance ?? "—",
                                    },
                                    {
                                        key: "status",
                                        header: "Status",
                                        render: (r: StaffLeaveItem) => (
                                            <Badge
                                                tone={
                                                    r.status === "Approved"
                                                        ? "green"
                                                        : r.status === "Rejected"
                                                          ? "red"
                                                          : "amber"
                                                }
                                            >
                                                {r.status}
                                            </Badge>
                                        ),
                                    },
                                ]}
                                rows={staffLeaves}
                                rowKey={(r) => r.id}
                                empty="No staff leave requests."
                            />
                        </>
                    )}
                </>
            )}
        </div>
    );
}
