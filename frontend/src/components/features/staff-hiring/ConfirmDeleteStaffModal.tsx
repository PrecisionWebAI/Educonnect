"use client";

import { useEffect, useState } from "react";
import { Button, Input, Modal } from "@/components/ui";
import type { StaffProfileRow } from "@/types";

// Type-to-confirm deletion for a hired staff member (Hired tab).
// The destructive button stays disabled until the operator types the exact
// phrase `delete <name>`, so a misclick can never remove an employee.

export default function ConfirmDeleteStaffModal({
    staff,
    deleting,
    onClose,
    onConfirm,
}: {
    staff: StaffProfileRow | null;
    deleting: boolean;
    onClose: () => void;
    onConfirm: () => void;
}) {
    const [typed, setTyped] = useState("");
    const name = staff?.fullName ?? "";
    const confirmText = name ? `Delete ${name}` : "";

    // Reset the input each time a different employee opens the modal.
    useEffect(() => {
        setTyped("");
    }, [staff?.id]);

    const matches = typed.trim().toLowerCase() === confirmText.toLowerCase();

    return (
        <Modal open={staff !== null} title="Delete employee" onClose={onClose}>
            <div className="space-y-4">
                <p className="text-muted-foreground text-sm">
                    This permanently deletes <strong>{name}</strong> (
                    {staff?.employeeCode}) and their login. This cannot be undone.
                </p>
                <p className="text-sm">
                    To confirm, type{" "}
                    <strong className="text-destructive">&quot;{confirmText}&quot;</strong>{" "}
                    below.
                </p>
                <Input
                    label={`Type "${confirmText}" to confirm`}
                    value={typed}
                    placeholder={confirmText}
                    onChange={(e) => setTyped(e.target.value)}
                />
                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={onClose} disabled={deleting}>
                        Cancel
                    </Button>
                    <Button
                        variant="danger"
                        disabled={!matches || deleting}
                        loading={deleting}
                        onClick={onConfirm}
                    >
                        Delete employee
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
