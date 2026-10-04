"use client";

import { useState } from "react";
import { Button, Input, Modal, Select } from "@/components/ui";
import { todayISO } from "@/lib/format";
import type { AdmissionApplicationRow, SeparationRecord, SeparationSession } from "@/types";
import {
    SEPARATION_REASON_OPTIONS,
    SEPARATION_SESSION_OPTIONS,
    droppedClassOf,
    studentName,
} from "./admission-options";

// Separation — opened from the Registered table "Action" button.
// The dropped class is fixed (it is the student's current class); the
// reason + completed/incomplete session are what feed the Inactive and
// "mid-session dropped" numbers.

export default function SeparationModal({
    student,
    onClose,
    onSubmit,
}: {
    student: AdmissionApplicationRow | null;
    onClose: () => void;
    onSubmit: (id: number, record: SeparationRecord) => void;
}) {
    const [reason, setReason] = useState("");
    const [session, setSession] = useState<SeparationSession>("Incomplete Session");
    const [date, setDate] = useState("");
    const [prevStudent, setPrevStudent] = useState<AdmissionApplicationRow | null>(null);

    // Re-seed the form whenever a different student is opened.
    if (student && student !== prevStudent) {
        setPrevStudent(student);
        setReason(student.separation?.reason ?? "");
        setSession(student.separation?.session ?? "Incomplete Session");
        setDate(student.separation?.date ?? todayISO());
    }

    return (
        <Modal
            open={student !== null}
            title={student ? `Separation — ${studentName(student)}` : "Separation"}
            onClose={onClose}
        >
            {student && (
                <div className="space-y-4">
                    <Input label="Dropped class" value={droppedClassOf(student)} disabled />
                    <Input label="Section" value={student.appliedSectionPreference || "—"} disabled />
                    <Select
                        label="Reason"
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                    >
                        <option value="">Select a reason…</option>
                        {SEPARATION_REASON_OPTIONS.map((r) => (
                            <option key={r} value={r}>
                                {r}
                            </option>
                        ))}
                    </Select>
                    <Select
                        label="Session"
                        value={session}
                        onChange={(e) => setSession(e.target.value as SeparationSession)}
                    >
                        {SEPARATION_SESSION_OPTIONS.map((s) => (
                            <option key={s} value={s}>
                                {s}
                            </option>
                        ))}
                    </Select>
                    <Input
                        label="Date of leaving"
                        type="date"
                        value={date}
                        onChange={(e) => setDate(e.target.value)}
                    />
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={onClose}>
                            Cancel
                        </Button>
                        <Button
                            variant="danger"
                            onClick={() =>
                                onSubmit(student.id, {
                                    droppedClass: droppedClassOf(student),
                                    reason: reason || "Others",
                                    session,
                                    date: date || todayISO(),
                                })
                            }
                        >
                            Confirm Separation
                        </Button>
                    </div>
                </div>
            )}
        </Modal>
    );
}
