"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Input } from "@/components/ui";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import {
    addStudentGuardian,
    getStudentGuardians,
    removeStudentGuardian,
    updateStudentGuardian,
} from "@/services/students.service";
import type { GuardianInput, GuardianLink } from "@/types";

// The guardians of one student - the **same card** on the Students directory and on the
// admission Registered view, so a family is edited in one place and reads the same
// everywhere.
//
// What it knows about the rule (`app/core/contacts.py` on the server):
//   * one guardian is one **person** - adding a contact the school already has links
//     that person (a sibling's parent) instead of making a second row;
//   * a number or address another family holds comes back as a refusal naming them;
//   * a brand-new login is handed over here, once, with its first-time password;
//   * remove takes the guardian off **this** child only: their login and their other
//     children are untouched.

const RELATIONS = ["father", "mother", "guardian", "other"];

const EMPTY: GuardianInput = {
    name: "",
    phone: "",
    relation: "guardian",
    email: "",
    alternate_phone: "",
    occupation: "",
    address: "",
    is_primary: false,
};

/** Ten digits, however the office typed the number. */
function digitsOf(value: string): string {
    return (value || "").replace(/\D/g, "");
}

export default function GuardianCard({
    studentId,
    className,
}: {
    studentId: string;
    className?: string;
}) {
    const toast = useToast();
    const [rows, setRows] = useState<GuardianLink[]>([]);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [open, setOpen] = useState(false);
    const [editing, setEditing] = useState<string | null>(null);
    const [confirmId, setConfirmId] = useState<string | null>(null);
    const [draft, setDraft] = useState<GuardianInput>(EMPTY);
    const [error, setError] = useState("");

    const load = useCallback(async () => {
        setLoading(true);
        try {
            setRows(await getStudentGuardians(studentId));
        } catch (err) {
            setError(errorMessage(err, "Could not load the guardians"));
        } finally {
            setLoading(false);
        }
    }, [studentId]);

    useEffect(() => {
        void load();
    }, [load]);

    function startAdd() {
        setDraft(EMPTY);
        setEditing(null);
        setError("");
        setOpen(true);
    }

    function startEdit(row: GuardianLink) {
        setDraft({
            name: row.name,
            phone: row.phone,
            relation: row.relation,
            email: row.email ?? "",
            alternate_phone: row.alternatePhone ?? "",
            occupation: row.occupation ?? "",
            address: row.address ?? "",
            is_primary: row.isPrimary,
        });
        setEditing(row.guardianId);
        setError("");
        setOpen(true);
    }

    async function save() {
        if (!draft.name.trim()) {
            setError("The guardian's name is required");
            return;
        }
        if (digitsOf(draft.phone).length !== 10) {
            setError("Phone must be exactly 10 digits");
            return;
        }
        setBusy(true);
        setError("");
        try {
            const saved = editing
                ? await updateStudentGuardian(studentId, editing, draft)
                : await addStudentGuardian(studentId, draft);
            await load();
            setOpen(false);
            toast.push("success", `${saved.name} saved`);
            if (saved.password && saved.loginEmail) {
                // The one moment the password exists: only its hash is stored.
                toast.push(
                    "info",
                    `Login ${saved.loginEmail} created — first-time password ${saved.password} (copy it now)`,
                );
            }
        } catch (err) {
            setError(errorMessage(err, "Could not save the guardian"));
        } finally {
            setBusy(false);
        }
    }

    async function remove(row: GuardianLink) {
        // Two clicks, so a slip of the mouse cannot unlink a family.
        if (confirmId !== row.guardianId) {
            setConfirmId(row.guardianId);
            return;
        }
        setBusy(true);
        setError("");
        try {
            const result = await removeStudentGuardian(studentId, row.guardianId);
            await load();
            setConfirmId(null);
            toast.push(
                "success",
                `${row.name} removed from this student` +
                    (result.primaryMovedTo
                        ? ` — ${result.primaryMovedTo} is now the primary contact`
                        : ""),
            );
        } catch (err) {
            setError(errorMessage(err, "Could not remove the guardian"));
        } finally {
            setBusy(false);
        }
    }

    return (
        <div
            className={
                className ?? "glass-card space-y-3 border border-(--border-subtle) p-5"
            }
        >
            <div className="flex items-center justify-between border-b border-(--border-subtle) pb-2">
                <h4 className="text-foreground font-semibold">Guardians</h4>
                <Button variant="outline" size="sm" onClick={startAdd}>
                    + Add
                </Button>
            </div>

            {loading && (
                <p className="text-muted-foreground text-sm">Loading guardians…</p>
            )}
            {!loading && rows.length === 0 && (
                <p className="text-muted-foreground text-sm">
                    Nobody on file yet — add the family&apos;s contact, and the login
                    comes with it.
                </p>
            )}

            <ul className="space-y-3">
                {rows.map((row) => (
                    <li
                        key={row.linkId}
                        className="rounded-lg border border-(--border-subtle) p-3"
                    >
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <div className="text-foreground text-sm font-medium">
                                    {row.name}{" "}
                                    <span className="text-muted-foreground text-xs">
                                        ({row.relation})
                                    </span>
                                </div>
                                <div className="text-muted-foreground text-xs">
                                    {row.phone}
                                    {row.email ? ` · ${row.email}` : ""}
                                </div>
                                <div className="text-muted-foreground text-xs">
                                    Login: {row.loginEmail ?? "—"}
                                </div>
                            </div>
                            <div className="flex shrink-0 items-center gap-2">
                                {row.isPrimary && <Badge tone="green">Primary</Badge>}
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => startEdit(row)}
                                >
                                    Edit
                                </Button>
                                <Button
                                    variant="danger"
                                    size="sm"
                                    disabled={busy}
                                    onClick={() => void remove(row)}
                                >
                                    {confirmId === row.guardianId
                                        ? "Confirm"
                                        : "Remove"}
                                </Button>
                            </div>
                        </div>
                    </li>
                ))}
            </ul>

            {open && (
                <div className="space-y-3 rounded-lg border border-(--border-subtle) p-3">
                    <div className="grid gap-3 sm:grid-cols-2">
                        <div className="space-y-1">
                            <Label htmlFor="guardian-name">Name *</Label>
                            <Input
                                id="guardian-name"
                                value={draft.name}
                                onChange={(e) =>
                                    setDraft({ ...draft, name: e.target.value })
                                }
                            />
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="guardian-relation">Relation</Label>
                            <select
                                id="guardian-relation"
                                className="h-9 w-full rounded-md border border-(--border-subtle) bg-transparent px-2 text-sm"
                                value={draft.relation ?? "guardian"}
                                onChange={(e) =>
                                    setDraft({ ...draft, relation: e.target.value })
                                }
                            >
                                {RELATIONS.map((relation) => (
                                    <option key={relation} value={relation}>
                                        {relation}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="guardian-phone">Phone *</Label>
                            <Input
                                id="guardian-phone"
                                value={draft.phone}
                                onChange={(e) =>
                                    setDraft({ ...draft, phone: e.target.value })
                                }
                            />
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="guardian-email">Email (their login)</Label>
                            <Input
                                id="guardian-email"
                                type="email"
                                value={draft.email ?? ""}
                                onChange={(e) =>
                                    setDraft({ ...draft, email: e.target.value })
                                }
                            />
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="guardian-alt">Alternate phone</Label>
                            <Input
                                id="guardian-alt"
                                value={draft.alternate_phone ?? ""}
                                onChange={(e) =>
                                    setDraft({
                                        ...draft,
                                        alternate_phone: e.target.value,
                                    })
                                }
                            />
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="guardian-occupation">Occupation</Label>
                            <Input
                                id="guardian-occupation"
                                value={draft.occupation ?? ""}
                                onChange={(e) =>
                                    setDraft({ ...draft, occupation: e.target.value })
                                }
                            />
                        </div>
                    </div>

                    <label className="text-muted-foreground flex items-center gap-2 text-sm">
                        <input
                            type="checkbox"
                            checked={Boolean(draft.is_primary)}
                            onChange={(e) =>
                                setDraft({ ...draft, is_primary: e.target.checked })
                            }
                        />
                        Primary contact for this child
                    </label>

                    {error && <p className="text-sm text-(--danger)">{error}</p>}

                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => setOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            loading={busy}
                            onClick={() => void save()}
                        >
                            {editing ? "Save changes" : "Add guardian"}
                        </Button>
                    </div>
                </div>
            )}

            {error && !open && <p className="text-sm text-(--danger)">{error}</p>}
        </div>
    );
}
