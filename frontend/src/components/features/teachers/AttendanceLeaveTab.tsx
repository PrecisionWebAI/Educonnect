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
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { todayISO } from "@/lib/format";
import { draftEntries, withDraftValue, type Draft } from "@/lib/staff-attendance/draft";
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

/** What the record filter offers: the five words a register row may show. */
const STATUS_OPTIONS: { value: string; label: string }[] = [
    { value: "All", label: "Filter by record" },
    { value: "present", label: "Present" },
    { value: "absent", label: "Absent" },
    { value: "half_day", label: "Half Day" },
    { value: "on_leave", label: "On Leave" },
    { value: "not_marked", label: "Not Marked" },
];

/**
 * "12 Nov, 14:32" for a server timestamp. The API sends UTC without a zone marker, so one is
 * added before parsing - otherwise the browser would read it as local time and shift it.
 */
function updatedAtLabel(value: string): string {
    const stamp = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
    const date = new Date(stamp);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
    });
}

/** The three words a caller may record (the server refuses anything else). */
const MARK_OPTIONS = [
    { value: "present", label: "Present" },
    { value: "absent", label: "Absent" },
    { value: "half_day", label: "Half Day" },
] as const;

/**
 * The "Attendance" tab: the day's register, and the leave requests.
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
    const [view, setView] = useState<"Register" | "Leaves">(
        canViewAttendance ? "Register" : "Leaves",
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

    const toast = useToast();
    const a = useAttendance({ canView: canViewAttendance, canMark, date });
    const register = a.register;

    /** The school is closed that day (weekly off, holiday): nothing can be marked. */
    const closed = register !== null && register.isOpen === false;
    /**
     * Who "Mark All Present" would mark: only the people **nobody has marked yet**. Somebody
     * already Absent or Half Day keeps that mark (it was a decision, not a gap), and
     * approved leave is skipped because the server refuses those rows - one refused row
     * would take the whole day's payload with it.
     */
    const unmarked = (register?.rows ?? []).filter((row) => row.status === "not_marked");
    /**
     * The caller's own row for this day. Once it is recorded (or covered by approved leave)
     * "Mark my attendance" has nothing left to do, so it switches itself off for the date;
     * changing a recorded day is the office's correction, not a second self-mark.
     */
    const mine =
        register?.ownEmployeeId == null
            ? undefined
            : register.rows.find((row) => row.employeeId === register.ownEmployeeId);
    const myDayDone = mine !== undefined && (mine.isMarked || mine.status === "on_leave");

    async function markAllPresent() {
        if (closed || unmarked.length === 0) return;
        const done = await a.mark(
            unmarked.map((row) => ({ employeeId: row.employeeId, status: "present" })),
        );
        // The cards and the table above are refetched before this returns, so they already
        // show the new counts; the toast just says what happened.
        if (done) toast.push("success", `${unmarked.length} marked present for ${date}.`);
    }

    /** "Mark my attendance": the caller's own day, then the cards and the table refresh. */
    async function markMine() {
        const done = await a.markSelf(date);
        if (done) toast.push("success", `Your attendance is marked present for ${date}.`);
    }

    /**
     * Changes made in the dropdowns but **not saved**. Nothing is written until "Save
     * attendance", so the cards above keep describing what is really recorded. They belong to
     * the day they were made on: moving to another date leaves them behind.
     */
    const [draftState, setDraftState] = useState<{ date: string; values: Draft }>({
        date,
        values: {},
    });
    const draft: Draft = draftState.date === date ? draftState.values : {};
    const draftCount = Object.keys(draft).length;

    function chooseStatus(row: StaffAttendanceRow, value: string) {
        const mark = MARK_OPTIONS.find((option) => option.value === value);
        if (mark === undefined) return;
        setDraftState({ date, values: withDraftValue(draft, row, mark.value) });
    }

    /** "Save attendance": every drafted change in one call, then the cards move. */
    async function saveDraft() {
        const entries = draftEntries(register?.rows ?? [], draft);
        if (entries.length === 0) return;
        const done = await a.mark(entries);
        if (done) {
            setDraftState({ date, values: {} });
            toast.push(
                "success",
                `Saved ${entries.length} change${entries.length === 1 ? "" : "s"} for ${date}.`,
            );
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
                    {closed && !row.isMarked ? (
                        <Badge tone="muted">Closed</Badge>
                    ) : (
                        <Badge tone={TONE[row.status]}>{row.statusLabel}</Badge>
                    )}
                    {draft[row.employeeId] !== undefined && <Badge tone="amber">Unsaved</Badge>}
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
                        value={draft[row.employeeId] ?? (row.isMarked ? row.status : "")}
                        disabled={
                            row.status === "on_leave" ||
                            (closed && !row.isMarked) ||
                            a.busy !== null
                        }
                        onChange={(event) => chooseStatus(row, event.target.value)}
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
            // Whoever last set the day's value, and when: changing a value overrides it and
            // the name moves to the person who changed it.
            render: (row: StaffAttendanceRow) =>
                row.markedBy === null ? (
                    "—"
                ) : (
                    <div style={{ lineHeight: 1.2 }}>
                        <div>{row.markedBy}</div>
                        {row.markedAt !== null && (
                            <div className="text-muted-foreground text-[0.74rem]">
                                {updatedAtLabel(row.markedAt)}
                            </div>
                        )}
                    </div>
                ),
        },
        {
            key: "month",
            header: "Month",
            // A bordered button with an arrow, so it reads as something to press - the
            // plain ghost button looked like a label.
            render: (row: StaffAttendanceRow) => (
                <Button
                    variant="outline"
                    size="sm"
                    title={`Open ${row.name}'s month`}
                    aria-label={`Open ${row.name}'s month`}
                    onClick={() => setMonthFor({ id: row.employeeId, name: row.name })}
                >
                    Month ›
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
                tabs={canViewAttendance ? ["Register", "Leaves"] : ["Leaves"]}
                active={view}
                onChange={(next) => setView(next as "Register" | "Leaves")}
            />

            {view === "Leaves" && (
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
                            aria-label="Filter by record"
                            value={a.status}
                            onChange={(e) => a.setStatus(e.target.value)}
                        >
                            {STATUS_OPTIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </Select>
                        {canMark && draftCount > 0 && (
                            <>
                                <Button
                                    loading={a.busy === "mark"}
                                    onClick={() => void saveDraft()}
                                >
                                    {`Save attendance (${draftCount})`}
                                </Button>
                                <Button
                                    variant="ghost"
                                    disabled={a.busy !== null}
                                    onClick={() => setDraftState({ date, values: {} })}
                                >
                                    Discard
                                </Button>
                            </>
                        )}
                        {canMark && (
                            <Button
                                loading={a.busy === "mark"}
                                disabled={closed || unmarked.length === 0}
                                title={
                                    closed
                                        ? "The school is closed this day"
                                        : unmarked.length === 0
                                          ? "Everybody is already marked"
                                          : `Mark the ${unmarked.length} not yet marked as present`
                                }
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
                                disabled={closed || myDayDone}
                                title={
                                    closed
                                        ? "The school is closed this day"
                                        : myDayDone
                                          ? `Your attendance for ${date} is already recorded (${mine?.statusLabel})`
                                          : "Mark yourself present for this day"
                                }
                                onClick={() => void markMine()}
                            >
                                {myDayDone ? "Attendance marked" : "Mark my attendance"}
                            </Button>
                        )}
                    </div>

                    <p className="text-muted-foreground mb-2 text-sm">
                        {register === null
                            ? "Loading the register…"
                            : closed
                              ? `${register.weekday}, ${register.date} — school closed (${register.closedReason}). No attendance is taken.`
                              : `${register.weekday}, ${register.date} — ${register.total} on the roll, ${register.marked} marked.`}
                    </p>

                    {draftCount > 0 && (
                        // A calm notice, not an error: nothing is wrong, the changes are simply
                        // waiting for the Save button.
                        <div
                            role="status"
                            className="bg-muted/50 mb-3 flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm"
                        >
                            <Badge tone="amber">
                                {draftCount} unsaved change{draftCount === 1 ? "" : "s"}
                            </Badge>
                            <span className="text-muted-foreground">
                                The summary above shows saved attendance only. Select{" "}
                                <b className="text-foreground">Save attendance</b> to apply these
                                changes.
                            </span>
                        </div>
                    )}

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
                            rows={a.rows}
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
