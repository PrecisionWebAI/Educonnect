"use client";
import { useMemo, useState } from "react";
import {
    Badge,
    Button,
    Input,
    Modal,
    Select,
    Spinner,
    Table,
    Textarea,
    type BadgeTone,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { todayISO } from "@/lib/format";
import type { StaffLeaveItem } from "@/types";
import LeavePolicyModal from "./LeavePolicyModal";
import { useLeaveWorkflow } from "./useLeaveWorkflow";
import type { StaffRows } from "./useStaff";

/** The colour each state wears - one map for the badges in both tables. */
const TONE: Record<StaffLeaveItem["status"], BadgeTone> = {
    Pending: "amber",
    Approved: "green",
    Rejected: "red",
    Cancelled: "muted",
};

/**
 * The Leave sub-view: balances, the request table, and the workflow that moves one
 * from Pending to Approved, Rejected or Cancelled.
 *
 * Three things are visible here rather than buried in the API:
 *
 * * **the balance is derived**, so the number beside a request is `entitled - used -
 *   pending` - cancelling a leave gives the days back in the same refresh, and `—`
 *   means "this school tracks no balance for this type", never "0 days left";
 * * **the buttons match the state**: Approve/Reject only on Pending, Cancel on
 *   Pending or Approved, and the server refuses the rest (`409`) with the state it
 *   is actually in - so the table never offers a click that cannot work;
 * * **the policy is the school's**, not the screen's: the apply form offers the types
 *   `GET /leave/policies` returns, so a school that never opened the policy screen
 *   still gets the three default types instead of an empty dropdown.
 */
export default function StaffLeavePanel({
    leaves,
    staff,
    canApply,
    canApprove,
    canReject,
    canRead,
    canManagePolicy,
}: {
    leaves: StaffLeaveItem[];
    /** The directory rows, for "file leave for somebody". */
    staff: StaffRows;
    /** `leave.create` - file a leave (own, or somebody's for the office). */
    canApply: boolean;
    /** `leave.approve` / `leave.reject` - decide somebody's request. */
    canApprove: boolean;
    canReject: boolean;
    /** `leave.read` - the policy list and the balance register. */
    canRead: boolean;
    /** `leave.manage_policy` - the policy table and per-person overrides. */
    canManagePolicy: boolean;
}) {
    const { push } = useToast();
    const [year, setYear] = useState(() => new Date().getFullYear());
    const [policyOpen, setPolicyOpen] = useState(false);
    const [applyOpen, setApplyOpen] = useState(false);
    const [decision, setDecision] = useState<{
        kind: "reject" | "cancel";
        row: StaffLeaveItem;
    } | null>(null);
    const [note, setNote] = useState("");

    const w = useLeaveWorkflow({ canRead, canManagePolicy, year });

    // --- the apply form ----------------------------------------------------
    const [employeeId, setEmployeeId] = useState("");
    const [leaveType, setLeaveType] = useState("");
    const [fromDate, setFromDate] = useState(todayISO());
    const [toDate, setToDate] = useState(todayISO());
    const [reason, setReason] = useState("");

    const types = useMemo(() => w.policies.map((policy) => policy.leaveType), [w.policies]);

    function openApply() {
        setEmployeeId(canApprove ? "" : "self");
        setLeaveType(types[0] ?? "");
        setFromDate(todayISO());
        setToDate(todayISO());
        setReason("");
        setApplyOpen(true);
    }

    async function submitApply() {
        const result = await w.apply({
            // "" means "for somebody" and the id is required; "self" files our own.
            employeeId: employeeId && employeeId !== "self" ? employeeId : null,
            leaveType,
            fromDate,
            toDate,
            reason: reason.trim() || undefined,
        });
        if (result === null) return;
        push(
            "success",
            `Leave filed for ${result.person} (${result.days} day(s))` +
                (result.balanceRemaining === null
                    ? "."
                    : ` - ${result.balanceRemaining} day(s) left.`),
        );
        setApplyOpen(false);
    }

    async function submitDecision() {
        if (decision === null) return;
        const row = decision.row;
        const result =
            decision.kind === "reject"
                ? await w.reject(row.id, note.trim() || null)
                : await w.cancel(row.id, note.trim() || null);
        if (result === null) return;
        push(
            "success",
            decision.kind === "reject"
                ? `Rejected ${row.staffName || "the request"}'s leave.`
                : `Cancelled ${row.staffName || "the request"}'s leave.`,
        );
        setDecision(null);
        setNote("");
    }

    const cancelAllowed = canApprove || canApply;

    /** The balance register, one line per person and one column per leave type. */
    const balanceRows = useMemo(() => {
        const people = new Map<
            string,
            {
                employeeId: string;
                employeeCode: string;
                staffName: string;
                cells: Record<
                    string,
                    { remaining: number | null; used: number; entitled: number | null }
                >;
            }
        >();
        for (const row of w.balances?.rows ?? []) {
            const person = people.get(row.employeeId) ?? {
                employeeId: row.employeeId,
                employeeCode: row.employeeCode,
                staffName: row.staffName,
                cells: {},
            };
            person.cells[row.leaveType] = {
                remaining: row.remaining,
                used: row.used,
                entitled: row.entitled,
            };
            people.set(row.employeeId, person);
        }
        return Array.from(people.values()).sort((first, second) =>
            first.staffName.localeCompare(second.staffName),
        );
    }, [w.balances]);

    const typeColumns = w.balances?.types ?? types;

    return (
        <div>
            <div className="toolbar">
                <Input
                    type="number"
                    aria-label="Balance year"
                    min={2000}
                    max={2100}
                    value={year}
                    onChange={(event) => setYear(Number(event.target.value) || year)}
                />
                {canApply && <Button onClick={openApply}>Apply leave</Button>}
                {canManagePolicy && (
                    <Button variant="outline" onClick={() => setPolicyOpen(true)}>
                        Leave policy
                    </Button>
                )}
            </div>

            {w.writeError !== null && (
                <p className="mb-2 text-sm" style={{ color: "var(--danger, #b42318)" }}>
                    {errorMessage(w.writeError, "The leave was not saved.")}
                </p>
            )}

            {canRead && (
                <>
                    <h4 className="mt-2 mb-1 text-sm font-semibold">Balances for {year}</h4>
                    {w.balancesLoading ? (
                        <Spinner size="sm" />
                    ) : (
                        <Table
                            columns={[
                                {
                                    key: "staffName",
                                    header: "Teacher",
                                    render: (row: (typeof balanceRows)[number]) => (
                                        <div style={{ lineHeight: 1.2 }}>
                                            <div>{row.staffName || row.employeeCode}</div>
                                            <div
                                                style={{
                                                    color: "var(--muted)",
                                                    fontSize: "0.74rem",
                                                }}
                                            >
                                                {row.employeeCode}
                                            </div>
                                        </div>
                                    ),
                                },
                                ...typeColumns.map((type) => ({
                                    key: type,
                                    header: type,
                                    render: (row: (typeof balanceRows)[number]) => {
                                        const cell = row.cells[type];
                                        if (cell === undefined) return "—";
                                        return (
                                            <div style={{ lineHeight: 1.2 }}>
                                                <b>{cell.remaining ?? "—"}</b>
                                                <div
                                                    style={{
                                                        color: "var(--muted)",
                                                        fontSize: "0.72rem",
                                                    }}
                                                >
                                                    {cell.used} of {cell.entitled ?? "—"} used
                                                </div>
                                            </div>
                                        );
                                    },
                                })),
                            ]}
                            rows={balanceRows}
                            rowKey={(row) => row.employeeId}
                            empty="Nobody is on the staff roll this year."
                        />
                    )}
                    <p className="text-muted-foreground mt-1 mb-3 text-xs">
                        Left = entitled − used − pending. “—” means this school tracks no balance
                        for that type, which is not the same as 0 days left.
                    </p>
                </>
            )}

            <h4 className="mt-2 mb-1 text-sm font-semibold">Leave requests</h4>
            <Table
                columns={[
                    {
                        key: "staffName",
                        header: "Teacher",
                        render: (row: StaffLeaveItem) => (
                            <div style={{ lineHeight: 1.2 }}>
                                <div>{row.staffName || "—"}</div>
                                <div style={{ color: "var(--muted)", fontSize: "0.74rem" }}>
                                    {row.staffCode || row.role}
                                </div>
                            </div>
                        ),
                    },
                    { key: "leaveType", header: "Type" },
                    {
                        key: "dates",
                        header: "Dates",
                        render: (row: StaffLeaveItem) => `${row.fromDate} → ${row.toDate}`,
                    },
                    { key: "days", header: "Days" },
                    {
                        key: "balance",
                        header: "Balance",
                        render: (row: StaffLeaveItem) => (row.balance === null ? "—" : row.balance),
                    },
                    {
                        key: "decided",
                        header: "Decision",
                        render: (row: StaffLeaveItem) =>
                            row.decidedBy === null ? (
                                "—"
                            ) : (
                                <div style={{ lineHeight: 1.2 }}>
                                    <div>{row.decidedBy}</div>
                                    <div
                                        style={{
                                            color: "var(--muted)",
                                            fontSize: "0.72rem",
                                        }}
                                    >
                                        {row.decidedAt ?? ""}
                                        {row.decisionNote ? ` · ${row.decisionNote}` : ""}
                                    </div>
                                </div>
                            ),
                    },
                    {
                        key: "status",
                        header: "Status",
                        render: (row: StaffLeaveItem) => (
                            <Badge tone={TONE[row.status] ?? "muted"}>{row.status}</Badge>
                        ),
                    },
                    {
                        key: "actions",
                        header: "",
                        render: (row: StaffLeaveItem) => (
                            <div className="flex gap-1">
                                {row.status === "Pending" && canApprove && (
                                    <Button
                                        variant="success"
                                        loading={w.busy === `approve-${row.id}`}
                                        onClick={async () => {
                                            const done = await w.approve(row.id);
                                            if (done !== null) {
                                                push("success", "Leave approved.");
                                            }
                                        }}
                                    >
                                        Approve
                                    </Button>
                                )}
                                {row.status === "Pending" && canReject && (
                                    <Button
                                        variant="danger"
                                        loading={w.busy === `reject-${row.id}`}
                                        onClick={() => {
                                            setNote("");
                                            setDecision({ kind: "reject", row });
                                        }}
                                    >
                                        Reject
                                    </Button>
                                )}
                                {(row.status === "Pending" || row.status === "Approved") &&
                                    cancelAllowed && (
                                        <Button
                                            variant="ghost"
                                            loading={w.busy === `cancel-${row.id}`}
                                            onClick={() => {
                                                setNote("");
                                                setDecision({ kind: "cancel", row });
                                            }}
                                        >
                                            Cancel
                                        </Button>
                                    )}
                            </div>
                        ),
                    },
                ]}
                rows={leaves}
                rowKey={(row) => row.id}
                empty="No leave requests yet."
            />
            <p className="text-muted-foreground mt-2 text-xs">
                Approving a leave makes the day read On Leave in the register; cancelling gives the
                days back to the balance in the same refresh.
            </p>

            <Modal open={applyOpen} title="Apply for leave" onClose={() => setApplyOpen(false)}>
                <div className="space-y-3">
                    <label className="block text-sm">
                        For
                        <Select
                            value={employeeId}
                            onChange={(event) => setEmployeeId(event.target.value)}
                        >
                            <option value="self">Myself</option>
                            {canApprove &&
                                staff
                                    .filter((person) => person.status !== "Inactive")
                                    .map((person) => (
                                        <option key={person.id} value={person.id}>
                                            {person.name} ({person.staffCode})
                                        </option>
                                    ))}
                        </Select>
                    </label>

                    <label className="block text-sm">
                        Leave type
                        <Select
                            value={leaveType}
                            onChange={(event) => setLeaveType(event.target.value)}
                        >
                            {types.map((type) => (
                                <option key={type} value={type}>
                                    {type}
                                </option>
                            ))}
                        </Select>
                    </label>

                    <div className="flex gap-2">
                        <label className="block flex-1 text-sm">
                            From
                            <Input
                                type="date"
                                value={fromDate}
                                onChange={(event) => {
                                    setFromDate(event.target.value);
                                    // A backwards range is refused at the edge, so the
                                    // end follows the start by default.
                                    if (event.target.value > toDate) {
                                        setToDate(event.target.value);
                                    }
                                }}
                            />
                        </label>
                        <label className="block flex-1 text-sm">
                            To
                            <Input
                                type="date"
                                min={fromDate}
                                value={toDate}
                                onChange={(event) => setToDate(event.target.value)}
                            />
                        </label>
                    </div>

                    <label className="block text-sm">
                        Reason
                        <Textarea
                            rows={3}
                            value={reason}
                            onChange={(event) => setReason(event.target.value)}
                            placeholder="What the office should know"
                        />
                    </label>

                    {w.writeError !== null && (
                        <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                            {errorMessage(w.writeError, "The leave was not filed.")}
                        </p>
                    )}

                    <div className="flex justify-end gap-2">
                        <Button variant="ghost" onClick={() => setApplyOpen(false)}>
                            Close
                        </Button>
                        <Button
                            loading={w.busy === "apply"}
                            disabled={!leaveType || !fromDate || !toDate}
                            onClick={() => void submitApply()}
                        >
                            File leave
                        </Button>
                    </div>
                </div>
            </Modal>

            <Modal
                open={decision !== null}
                title={decision?.kind === "reject" ? "Reject leave" : "Cancel leave"}
                onClose={() => setDecision(null)}
            >
                <div className="space-y-3">
                    <p className="text-muted-foreground text-sm">
                        {decision?.kind === "reject"
                            ? `${decision.row.staffName || "This teacher"} will see why the request was refused.`
                            : "The days go back to the balance, and the register stops reading On Leave for them."}
                    </p>
                    <Textarea
                        rows={3}
                        aria-label="Decision note"
                        value={note}
                        onChange={(event) => setNote(event.target.value)}
                        placeholder={
                            decision?.kind === "reject"
                                ? "e.g. clashes with the annual exam"
                                : "e.g. the trip was postponed"
                        }
                    />
                    {w.writeError !== null && (
                        <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                            {errorMessage(w.writeError, "The decision was not saved.")}
                        </p>
                    )}
                    <div className="flex justify-end gap-2">
                        <Button variant="ghost" onClick={() => setDecision(null)}>
                            Close
                        </Button>
                        <Button
                            variant={decision?.kind === "reject" ? "danger" : "primary"}
                            loading={
                                decision !== null &&
                                w.busy === `${decision.kind}-${decision.row.id}`
                            }
                            onClick={() => void submitDecision()}
                        >
                            {decision?.kind === "reject" ? "Reject" : "Cancel leave"}
                        </Button>
                    </div>
                </div>
            </Modal>

            <LeavePolicyModal
                open={policyOpen}
                policies={w.policies}
                busy={w.busy === "policies"}
                error={w.writeError}
                onClose={() => setPolicyOpen(false)}
                onSave={w.savePolicies}
                onRemove={w.removePolicy}
            />
        </div>
    );
}
