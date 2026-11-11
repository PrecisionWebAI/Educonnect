"use client";

import { Badge, Button, Modal } from "@/components/ui";
import type { AdmissionApplicationRow } from "@/types";
import AdmissionForm from "./AdmissionForm";
import GuardianCard from "../classroom/students/GuardianCard";
import { studentName, studentStatus } from "./admission-options";

// Read-only copy of the admission form with an "Edit" button that loads the
// record back into the Admission tab for changes.

export default function AdmissionDetailModal({
    application,
    onClose,
    onEdit,
}: {
    application: AdmissionApplicationRow | null;
    onClose: () => void;
    onEdit: (application: AdmissionApplicationRow) => void;
}) {
    return (
        <Modal
            open={application !== null}
            title={application ? studentName(application) || "Student" : ""}
            onClose={onClose}
        >
            {application && (
                <div>
                    <div className="mb-4 flex items-center gap-2">
                        {/* The row **is** the student, so the badges are the roll: the
                            number the school filed them under and whether they are
                            still on it. */}
                        <Badge tone="muted">{application.admissionNumber || "No number"}</Badge>
                        <Badge tone={studentStatus(application) === "Active" ? "green" : "muted"}>
                            {studentStatus(application)}
                        </Badge>
                        <span className="text-muted-foreground text-xs">
                            Admitted {application.createdOn}
                        </span>
                    </div>

                    {/* smaller popup: the form scrolls inside instead of growing */}
                    <div className="max-h-[56vh] overflow-y-auto pr-2">
                        <AdmissionForm value={application} readOnly columns="single" />

                        {/* The family this child is linked to: a guardian is a person of
                            their own, so the card edits them (and their other children's
                            records move with the change). */}
                        {application.studentId && (
                            <div className="mt-4">
                                <GuardianCard studentId={application.studentId} />
                            </div>
                        )}
                    </div>

                    <div className="modal-actions">
                        <Button variant="outline" onClick={onClose}>
                            Close
                        </Button>
                        <Button variant="primary" icon="✎" onClick={() => onEdit(application)}>
                            Edit
                        </Button>
                    </div>
                </div>
            )}
        </Modal>
    );
}
