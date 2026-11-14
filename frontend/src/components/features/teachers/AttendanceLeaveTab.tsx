"use client";
import { useState } from "react";
import {
    Badge,
    Button,
    Input,
    Select,
    Spinner,
    Table,
    Tabs,
    type BadgeTone,
} from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { todayISO } from "@/lib/format";
import type { StaffAttendanceRow, StaffAttendanceStatus, StaffLeaveItem } from "@/types";
import type { StaffRows } from "./useStaff";
import StaffLeavePanel from "./StaffLeavePanel";
import LeaveTabsPanel from "./LeaveTabsPanel";
import StaffMonthSheet from "./StaffMonthSheet";
import { useAttendance } from "./useAttendance";

/** The colour each status wears - one map for the badge, the chips and the tiles. */
const TONE: Record<StaffAttendanceStatus, BadgeTone> = {
    present: "green",
    absent: "red",
    half_day: "amber",
    on_leave: "teal",
    not_marked: "muted",
};

/** What the status filter offers: the five words a register row may show. */
const STATUS_OPTIONS: { value: string; label: string }[] = [
    { value: "All", label: "All statuses" },
    { value: "present", label: "Present" },
    { value: "absent", label: "Absent" },
    { value: "half_day", label: "Half Day" },
    { value: "on_leave", label: "On Leave" },
    { value: "not_marked", label: "Not Marked" },
];

/** The three words a caller may record (the server refuses anything else). */
const MARK_OPTIONS = [
    { value: "present", label: "Present" },
    { value: "absent", label: "Absent" },
    { value: "half_day", label: "Half Day" },
] as const;

type Markable = (typeof MARK_OPTIONS)[number]["value"];

/**
 * The "Attendance & Leave" tab: the day's register, and the leave requests.
 *
 * The register is the school's daily book, so three rules are visible here rather
 * than buried in the API:
 *
 * * **everybody on the roll has a line**, marked or not - the answer to "who has
 *   not been marked yet" is the person with no badge;
 * * **leave cannot be marked.** An `On Leave` row has no selector: the server
 *   derives that word from the approved leave, and would refuse the write (`409`);
 * * **the tiles describe the day**, so the status filter narrows the table without
 *   rewriting the counts above it.
 */
export default function AttendanceLeaveTab({
    leaves,
    staff,
    canViewAttendance,
    canMark,
    canMarkSelf,
    canViewLeave,
    canApplyLeave,
    canApproveLeave,
    canRejectLeave,
    canManageLeavePolicy,
}: {
    leaves: StaffLeaveItem[];
    /** The directory rows, so the office can file leave for somebody. */
    staff: StaffRows;
    /** `staff_attendance.read` - the register, at the caller's scope. */
    canViewAttendance: boolean;
    /** `staff_attendance.mark` - today's roll and a correction to it. */
    canMark: boolean;
    /** `staff_attendance.self` - your own day, once (the token decides whose). */
    canMarkSelf: boolean;
    /** `leave.read` - the leave list, its balances and the policy table. */
    canViewLeave: boolean;
    /** `leave.create` - file a leave (own, or somebody's for the office). */
    canApplyLeave: boolean;
    /** `leave.approve` / `leave.reject` - decide somebody's request. */
    canApproveLeave: boolean;
    canRejectLeave: boolean;
    /** `leave.manage_policy` - the school's types and one person's override. */
    canManageLeavePolicy: boolean;
}) {
    const [view, setView] = useState<"Register" | "Leave">(
        canViewAttendance ? "Register" : "Leave",
    );
    /**
     * The Teachers/Staff module shows leave **read-only** (Phase 6): applying,
     * approving and rejecting live on Leave & Applications, where the workflow's
     * own screens and permissions are. The record here is for reading.
     */
    const readOnlyModule = true;
    const [date, setDate] = useState(todayISO());
    /** The person whose month is open, and their name for the sheet's title. */
    const [monthFor, setMonthFor] = useState<{ id: string; name: string } | null>(null);

    const a = useAttendance({ canView: canViewAttendance, canMark, date });
    const register = a.register;

    async function markAllPresent() {
        if (register === null) return;
        // Approved leave is skipped: the server refuses those rows, and one refused
        // row would take the whole day's payload with it.
        const rows = register.rows.filter((row) => row.status !== "on_leave");
        if (rows.length === 0) return;
        await a.mark(rows.map((row) => ({ employeeId: row.employeeId, status: "present" })));
    }

    async function setStatus(recordId: string | null, employeeId: string, status: string) {
        const mark = MARK_OPTIONS.find((option) => option.value === status);
        if (mark === undefined) return;
        if (recordId === null) {
            await a.mark([{ employeeId, status: mark.value as Markable }]);
        } else {
            await a.amend(recordId, { status: mark.value as Markable });
        }
    }

    const columns = [
        {
            key: "name",
            header: "Teacher",
            render: (row: StaffAttendanceRow) => (
                <div style={{ lineHeight: 1.2 }}>
                    <div>{row.name}</div>
                    <div className="text-muted-foreground text-[0.74rem]">
                        {row.employeeCode || row.department}
                    </div>
                </div>
            ),
        },
        { key: "department", header: "Department" },
        {
            key: "status",
            header: "Status",
            render: (row: StaffAttendanceRow) => (
                <div className="flex items-center gap-2">
                    <Badge tone={TONE[row.status]}>{row.statusLabel}</Badge>
                    {row.leaveType !== null && (
                        <span className="text-muted-foreground text-xs">{row.leaveType}</span>
                    )}
                </div>
            ),
        },
        {
            key: "mark",
            header: "Record",
            render: (row: StaffAttendanceRow) =>
                !canMark ? (
                    <span className="text-muted-foreground text-xs">—</span>
                ) : (
                    <Select
                        aria-label={`Status for ${row.name}`}
                        value={row.isMarked ? row.status : ""}
                        disabled={row.status === "on_leave" || a.busy !== null}
                        onChange={(event) =>
                            void setStatus(row.recordId, row.employeeId, event.target.value)
                        }
                    >
                        <option value="" disabled>
                            Not marked
                        </option>
                        {MARK_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </Select>
                ),
        },
        {
            key: "remarks",
            header: "Remarks",
            render: (row: StaffAttendanceRow) => row.remarks ?? "—",
        },
        {
            key: "markedBy",
            header: "Recorded by",
            render: (row: StaffAttendanceRow) => row.markedBy ?? "—",
        },
        {
            key: "month",
            header: "",
            render: (row: StaffAttendanceRow) => (
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setMonthFor({ id: row.employeeId, name: row.name })}
                >
                    Month
                </Button>
            ),
        },
    ];

    const tiles =
        register === null ? null : (
            <div className="stat-tiles">
                <div className="stat-tile">
                    <b>{register.present}</b>
                    <span>Present</span>
                </div>
                <div className="stat-tile">
                    <b>{register.halfDay}</b>
                    <span>Half Day</span>
                </div>
                <div className="stat-tile">
                    <b>{register.absent}</b>
                    <span>Absent</span>
                </div>
                <div className="stat-tile">
                    <b>{register.onLeave}</b>
                    <span>On Leave</span>
                </div>
                <div className="stat-tile">
                    {/* The office's to-do list: nobody has said anything about these yet. */}
                    <b>{register.notMarked}</b>
                    <span>Not Marked</span>
                </div>
                <div className="stat-tile">
                    <b>{register.percent}%</b>
                    <span>Attended</span>
                </div>
            </div>
        );

    return (
        <>
            <Tabs
                tabs={canViewAttendance ? ["Register", "Leave"] : ["Leave"]}
                active={view}
                onChange={(next) => setView(next as "Register" | "Leave")}
            />

            {view === "Leave" && (
                <>
                    <StaffLeavePanel
                        leaves={leaves}
                        staff={staff}
                        // Read-only in this module (`readOnlyModule` above): filing and
                        // deciding live on Leave & Applications; this tab is the record.
                        canApply={canApplyLeave && !readOnlyModule}
                        canApprove={canApproveLeave && !readOnlyModule}
                        canReject={canRejectLeave && !readOnlyModule}
                        canRead={canViewLeave}
                        canManagePolicy={canManageLeavePolicy}
                    />
                    <LeaveTabsPanel />
                </>
            )}

            {view === "Register" && canViewAttendance && (
                <>
                    {tiles}

                    <div className="toolbar">
                        <Input
                            type="date"
                            aria-label="Register date"
                            value={date}
                            max={todayISO()}
                            onChange={(event) => setDate(event.target.value || todayISO())}
                        />
                        <Select
                            value={a.department}
                            onChange={(e) => a.setDepartment(e.target.value)}
                        >
                            {a.departments.map((name) => (
                                <option key={name} value={name}>
                                    {name === "All" ? "All departments" : name}
                                </option>
                            ))}
                        </Select>
                        <Select value={a.status} onChange={(e) => a.setStatus(e.target.value)}>
                            {STATUS_OPTIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </Select>
                        {canMark && (
                            <Button
                                loading={a.busy === "mark"}
                                onClick={() => void markAllPresent()}
                            >
                                Mark All Present
                            </Button>
                        )}
                        {/* Your own day: `staff_attendance.self`, not the office's
                            `mark`. The server takes the person from the token, so
                            this button cannot mark anybody else. */}
                        {canMarkSelf && (
                            <Button
                                loading={a.busy === "self"}
                                onClick={() => void a.markSelf(todayISO())}
                            >
                                Mark my attendance
                            </Button>
                        )}
                    </div>

                    <p className="text-muted-foreground mb-2 text-sm">
                        {register === null
                            ? "Loading the register…"
                            : `${register.weekday}, ${register.date} — ${register.total} on the roll, ${register.marked} marked.`}
                    </p>

                    {a.writeError !== null && (
                        <p className="mb-2 text-sm" style={{ color: "var(--danger, #b42318)" }}>
                            {errorMessage(a.writeError, "The register was not saved.")}
                        </p>
                    )}

                    {a.loading ? (
                        <Spinner />
                    ) : a.error !== null ? (
                        <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                            {errorMessage(a.error, "The register could not be loaded.")}
                        </p>
                    ) : (
                        <Table
                            columns={columns}
                            rows={register?.rows ?? []}
                            rowKey={(row) => row.employeeId}
                            empty="Nobody is on the staff roll for this day."
                        />
                    )}

                    <p className="text-muted-foreground mt-2 text-xs">
                        Not Marked is not Absent: it means nobody has recorded that day yet. On
                        Leave comes from the approved leave, so it cannot be marked here.
                    </p>
                </>
            )}

            {/* Mounted only while a person's month is open. Rendering it always
                (with `employeeId === null`) left a Modal on screen whose query was
                disabled - and a disabled query is `pending` for ever, so the sheet
                showed a spinner above the register that never went away. */}
            {monthFor !== null && (
                <StaffMonthSheet
                    employeeId={monthFor.id}
                    employeeName={monthFor.name}
                    onClose={() => setMonthFor(null)}
                />
            )}
        </>
    );
}
