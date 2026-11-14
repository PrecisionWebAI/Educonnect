"use client";
import { useState } from "react";
import { Button, Input, Modal, Table } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import type { LeavePolicy } from "@/types";

/**
 * The school's leave types and how many days each grants.
 *
 * The table edits a **list**, and saving it upserts: a type the office removes is
 * retired with the Remove button (the server refuses while requests still use it),
 * not by being left out of the payload. Leaving a row out would be an omission
 * nobody can see, and omitting every row is exactly what "this school grants
 * nothing" looks like - two very different states that must not share a gesture.
 */
export default function LeavePolicyModal({
    open,
    policies,
    busy,
    error,
    onClose,
    onSave,
    onRemove,
}: {
    open: boolean;
    policies: LeavePolicy[];
    busy: boolean;
    error: unknown;
    onClose: () => void;
    onSave: (rows: { leaveType: string; annualDays: number }[]) => Promise<boolean>;
    onRemove: (leaveType: string) => Promise<boolean>;
}) {
    const [draft, setDraft] = useState<{ leaveType: string; annualDays: string }[]>([]);
    const [seeded, setSeeded] = useState(false);
    const [newType, setNewType] = useState("");

    // Seed the draft from the server's list when the dialog opens: the table is an
    // edit of what is stored, not a second copy kept in sync with it.
    if (open && !seeded) {
        setSeeded(true);
        setDraft(
            policies.map((policy) => ({
                leaveType: policy.leaveType,
                annualDays: String(policy.annualDays),
            })),
        );
    }

    function setDays(leaveType: string, value: string) {
        setDraft((rows) =>
            rows.map((row) => (row.leaveType === leaveType ? { ...row, annualDays: value } : row)),
        );
    }

    async function save() {
        const rows = draft
            .map((row) => ({
                leaveType: row.leaveType.trim(),
                annualDays: Number(row.annualDays),
            }))
            .filter((row) => row.leaveType.length > 0 && Number.isFinite(row.annualDays));
        if (rows.length === 0) return;
        const done = await onSave(rows);
        if (done) onClose();
    }

    return (
        <Modal open={open} title="Leave policy" onClose={onClose}>
            <div className="space-y-3">
                <p className="text-muted-foreground text-sm">
                    Days granted per year, per leave type. A type with 0 days stays on the list but
                    grants nothing - the requests already made keep their history.
                </p>

                <Table
                    columns={[
                        { key: "leaveType", header: "Leave type" },
                        {
                            key: "annualDays",
                            header: "Days a year",
                            render: (row: { leaveType: string; annualDays: string }) => (
                                <Input
                                    type="number"
                                    min={0}
                                    max={365}
                                    aria-label={`Days for ${row.leaveType}`}
                                    value={row.annualDays}
                                    onChange={(event) => setDays(row.leaveType, event.target.value)}
                                />
                            ),
                        },
                        {
                            key: "actions",
                            header: "",
                            render: (row: { leaveType: string }) => (
                                <Button
                                    variant="ghost"
                                    loading={busy}
                                    onClick={async () => {
                                        const done = await onRemove(row.leaveType);
                                        if (!done) return;
                                        setDraft((rows) =>
                                            rows.filter((item) => item.leaveType !== row.leaveType),
                                        );
                                    }}
                                >
                                    Remove
                                </Button>
                            ),
                        },
                    ]}
                    rows={draft}
                    rowKey={(row) => row.leaveType}
                    empty="No leave types yet - add one below."
                />

                <div className="toolbar">
                    <Input
                        placeholder="New leave type (e.g. Bereavement)"
                        aria-label="New leave type"
                        value={newType}
                        onChange={(event) => setNewType(event.target.value)}
                    />
                    <Button
                        variant="outline"
                        onClick={() => {
                            const name = newType.trim();
                            if (!name) return;
                            setDraft((rows) => [...rows, { leaveType: name, annualDays: "0" }]);
                            setNewType("");
                        }}
                    >
                        Add type
                    </Button>
                </div>

                {error !== null && (
                    <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                        {errorMessage(error, "The policy was not saved.")}
                    </p>
                )}

                <div className="flex justify-end gap-2">
                    <Button variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button loading={busy} onClick={() => void save()}>
                        Save policy
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
