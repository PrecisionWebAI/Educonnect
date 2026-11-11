"use client";

import { useState } from "react";
import { Button, Input, Modal } from "@/components/ui";
import type { AdmissionApplicationRow } from "@/types";
import { studentName } from "./admission-options";

// Type-to-confirm deletion for a registered student (Admission > Registered).
// The destructive button stays disabled until the operator types the exact
// phrase `delete <student name>`, so a misclick can never remove a student.
//
// The dialog carries a second, louder warning: a class-section exists because
// students sit in it, so deleting the **last** student of a class-section deletes
// that class-section too, with every record filed against it. The backend reports
// which one it removed (`classroomRemoved`), and the page toasts it afterwards.

/** "Class 12-J" for the class-section the application asked for, or "". */
function classSectionOf(student: AdmissionApplicationRow): string {
    const className = (student.appliedForClassLevel || "").trim();
    const section = (student.appliedSectionPreference || "").trim();
    if (className && section) return `${className}-${section}`;
    return className;
}

/**
 * The dialog's body, which owns the typed confirmation.
 *
 * The caller renders it with `key={student.id}`, so opening it for another student
 * mounts a fresh input: no effect is needed to reset it.
 */
function DeleteDialogBody({
    student,
    deleting,
    onClose,
    onConfirm,
}: {
    student: AdmissionApplicationRow;
    deleting: boolean;
    onClose: () => void;
    onConfirm: () => void;
}) {
    const [typed, setTyped] = useState("");
    const name = studentName(student);
    const confirmText = `Delete ${name}`;
    const classSection = classSectionOf(student);
    const matches = typed.trim().toLowerCase() === confirmText.toLowerCase();

    return (
        <div className="space-y-4">
            <p className="text-muted-foreground text-sm">
                This permanently deletes <strong>{name}</strong> and all their records (attendance,
                marks, homework, fees, logins). This cannot be undone.
            </p>

            <div className="border-destructive/40 bg-destructive/5 rounded-lg border p-3">
                <p className="text-destructive text-sm font-semibold">
                    Warning — this can delete a whole classroom
                </p>
                <p className="text-muted-foreground mt-1 text-sm">
                    {classSection ? (
                        <>
                            <strong>{name}</strong> is in <strong>{classSection}</strong>. If they
                            are the <strong>last student</strong> of that class-section, the
                            class-section itself is deleted with them — together with every record
                            filed against it:
                        </>
                    ) : (
                        <>
                            If this student is the <strong>last one</strong> in their class-section,
                            the class-section itself is deleted with them — together with every
                            record filed against it:
                        </>
                    )}{" "}
                    its attendance register, timetable, homework, class diary, syllabus progress and
                    teacher assignment.
                </p>
            </div>

            <p className="text-sm">
                To confirm, type{" "}
                <strong className="text-destructive">&ldquo;{confirmText}&rdquo;</strong> below.
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
    );
}

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
    return (
        <Modal open={student !== null} title="Delete student" onClose={onClose}>
            {student && (
                <DeleteDialogBody
                    key={student.id}
                    student={student}
                    deleting={deleting}
                    onClose={onClose}
                    onConfirm={onConfirm}
                />
            )}
        </Modal>
    );
}
