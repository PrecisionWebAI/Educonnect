"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Badge, Button, Input, Modal } from "@/components/ui";
import { staffRoleLabel } from "@/services";
import type { StaffLifecycleInput, StaffLifecycleResult, StaffProfileRow } from "@/types";

// The Hired tab's View popup: the whole staff member on one screen, with the actions
// that belong to that person inside it — Edit, Logins, Deactivate/Reactivate, Delete —
// the same shape the admission screen uses for a registered student.
//
// It opens on the record. The row's Deactivate button opens **the same popup with the
// lifecycle panel first**, so the office sees who they are about to switch off (their
// login, whether it stays open for their children) instead of a bare confirmation.

/** One label/value pair in the record. */
function Row({ label, value }: { label: string; value: ReactNode }) {
    return (
        <div className="text-sm">
            <div className="text-muted-foreground text-xs">{label}</div>
            <div>{value ?? "—"}</div>
        </div>
    );
}

function money(value: number | null): string | null {
    return value != null ? `₹${value.toLocaleString()}` : null;
}

function when(value: string | null): string | null {
    if (!value) return null;
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

export default function StaffDetailModal({
    staff,
    focus = "record",
    busy,
    onClose,
    onEdit,
    onLogins,
    onDelete,
    onDeactivate,
    onReactivate,
    onError,
}: {
    staff: StaffProfileRow | null;
    /** Where the popup opens: the record, or the lifecycle panel first. */
    focus?: "record" | "lifecycle";
    /** The lifecycle call in flight (the row id), so the button shows a spinner. */
    busy: string | null;
    onClose: () => void;
    onEdit: (row: StaffProfileRow) => void;
    onLogins: (row: StaffProfileRow) => void;
    onDelete: (row: StaffProfileRow) => void;
    onDeactivate: (
        row: StaffProfileRow,
        input: StaffLifecycleInput,
    ) => Promise<StaffLifecycleResult>;
    onReactivate: (
        row: StaffProfileRow,
        input?: StaffLifecycleInput,
    ) => Promise<StaffLifecycleResult>;
    /** The call was refused (`409` already off/on, `400` bad day) — show it. */
    onError: (error: unknown) => void;
}) {
    const [leftOn, setLeftOn] = useState("");
    const [reason, setReason] = useState("");
    const [running, setRunning] = useState(false);

    // A fresh popup for a different person starts with an empty lifecycle form.
    useEffect(() => {
        setLeftOn("");
        setReason("");
        setRunning(false);
    }, [staff?.id]);

    if (!staff) return null;

    const inFlight = running || busy === staff.id;

    async function run(action: (input: StaffLifecycleInput) => Promise<StaffLifecycleResult>) {
        setRunning(true);
        try {
            await action({ leftOn: leftOn || null, reason: reason || null });
            setReason("");
        } catch (error) {
            onError(error);
        } finally {
            setRunning(false);
        }
    }

    const lifecyclePanel = (
        <section className="rounded-lg border p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
                <b className="text-sm">
                    {staff.isActive ? "Their staff access is on" : "They are off the staff roll"}
                </b>
                {staff.isActive ? (
                    <Badge tone="green">Active</Badge>
                ) : (
                    <Badge tone="amber">{when(staff.leftOn) ?? "Left"}</Badge>
                )}
            </div>

            {staff.isActive ? (
                <>
                    <p className="text-muted-foreground text-sm">
                        Deactivating switches their <b>staff</b> access off: the roles they were
                        hired for are withdrawn and the day is stamped. Nothing is deleted, so the
                        salary register and the timetable still explain themselves. If they are
                        also a parent here, their login stays and they keep signing in.
                    </p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <Input
                            label="Last working day"
                            type="date"
                            value={leftOn}
                            onChange={(e) => setLeftOn(e.target.value)}
                        />
                        <Input
                            label="Reason (optional)"
                            value={reason}
                            placeholder="Resigned, contract ended…"
                            onChange={(e) => setReason(e.target.value)}
                        />
                    </div>
                    <div className="mt-3 flex justify-end">
                        <Button
                            variant="danger"
                            loading={inFlight}
                            onClick={() => run((input) => onDeactivate(staff, input))}
                        >
                            Deactivate staff access
                        </Button>
                    </div>
                </>
            ) : (
                <>
                    <p className="text-muted-foreground text-sm">
                        {staff.deactivatedRoles.length > 0 && (
                            <>
                                {staff.deactivatedRoles.map(staffRoleLabel).join(", ")} access was
                                withdrawn
                                {when(staff.leftOn) ? ` (left ${when(staff.leftOn)})` : ""}.{" "}
                            </>
                        )}
                        Reactivating gives exactly those roles back.
                        {staff.loginActive
                            ? " Their login signs in as usual."
                            : " Their login was switched off too — it opened nothing else."}
                    </p>
                    <div className="mt-3 flex justify-end">
                        <Button
                            variant="primary"
                            loading={inFlight}
                            onClick={() =>
                                run((input) =>
                                    onReactivate(staff, { reason: input.reason ?? null }),
                                )
                            }
                        >
                            Reactivate
                        </Button>
                    </div>
                </>
            )}
        </section>
    );

    const record = (
        <div className="grid gap-3 sm:grid-cols-2">
            <Row label="Employee ID" value={<b>{staff.employeeCode}</b>} />
            <Row label="Department" value={staff.department} />
            <Row
                label="Role"
                value={(staff.roleCodenames.length > 0
                    ? staff.roleCodenames
                    : [staff.roleCodename]
                )
                    .map(staffRoleLabel)
                    .join(", ")}
            />
            <Row label="Joined" value={when(staff.joiningDate)} />
            <Row
                label="Login"
                value={<code className="text-xs break-all">{staff.email}</code>}
            />
            <Row
                label="Login state"
                value={staff.loginActive ? "Signs in" : "Switched off"}
            />
            <Row label="Qualification" value={staff.qualification} />
            <Row label="Experience" value={`${staff.experienceYears} year(s)`} />
            <Row label="Contact email" value={staff.contactEmail} />
            <Row label="Phone" value={staff.phone} />
            <Row label="Address" value={staff.address} />
            <Row label="Emergency contact" value={staff.emergencyContact} />
            <Row label="Aadhaar" value={staff.aadhaarNo} />
            <Row label="PAN" value={staff.panNo} />
            <Row label="Bank" value={staff.bankName} />
            <Row label="Account" value={staff.bankAccountNo} />
            <Row label="IFSC" value={staff.ifsc} />
            <Row label="Monthly salary" value={money(staff.salaryMonthly)} />
            <Row label="Previous salary" value={money(staff.previousEmployerMonthlySalary)} />
        </div>
    );

    return (
        <Modal
            open
            title={`${staff.fullName} · ${staff.employeeCode}`}
            onClose={onClose}
        >
            <div>
                <div className="mb-3 flex items-center gap-2">
                    {staff.isActive ? (
                        <Badge tone="green">Active</Badge>
                    ) : (
                        <Badge tone="amber">{when(staff.leftOn) ?? "Left"}</Badge>
                    )}
                    <span className="text-muted-foreground text-xs">
                        Joined {when(staff.joiningDate) ?? "—"}
                    </span>
                </div>

                {/* smaller popup: the record scrolls inside instead of growing */}
                <div className="max-h-[56vh] overflow-y-auto pr-2">
                    {focus === "lifecycle" ? (
                        <div className="space-y-4">
                            {lifecyclePanel}
                            {record}
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {record}
                            {lifecyclePanel}
                        </div>
                    )}
                </div>

                <div className="modal-actions">
                    <Button variant="outline" onClick={onClose}>
                        Close
                    </Button>
                    <Button variant="outline" onClick={() => onLogins(staff)}>
                        Logins
                    </Button>
                    <Button variant="danger" onClick={() => onDelete(staff)}>
                        Delete
                    </Button>
                    <Button variant="primary" icon="✎" onClick={() => onEdit(staff)}>
                        Edit
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
