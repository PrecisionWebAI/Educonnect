"use client";

import { useEffect, useState } from "react";
import { Button, Input, Modal } from "@/components/ui";
import type { AdmissionApplicationRow } from "@/types";
import { studentName } from "./admission-options";

// Type-to-confirm deletion for a registered student (Admission > Registered).
// The destructive button stays disabled until the operator types the exact
// phrase `delete <student name>`, so a misclick can never remove a student.

export default function ConfirmDeleteAdmissionModal({
    student,
    deleting,
    onClose,
    onConfirm,
}: {
    student: AdmissionApplicationRow | null;
    deleting: boolean;
    onClose: () => void;
    onConfirm: () => void;
}) {
    const [typed, setTyped] = useState("");
    const name = student ? studentName(student) : "";
    const confirmText = name ? `Delete ${name}` : "";

    // Reset the input each time a different student opens the modal.
    useEffect(() => {
        setTyped("");
    }, [student?.id]);

    const matches = typed.trim().toLowerCase() === confirmText.toLowerCase();

    return (
        <Modal open={student !== null} title="Delete student" onClose={onClose}>
            <div className="space-y-4">
                <p className="text-muted-foreground text-sm">
                    This permanently deletes <strong>{name}</strong> and all their records
                    (attendance, homework, fees, logins). This cannot be undone.
                </p>
                <p className="text-sm">
                    To confirm, type <strong className="text-destructive">"{confirmText}"</strong>{" "}
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
                        Delete student
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
