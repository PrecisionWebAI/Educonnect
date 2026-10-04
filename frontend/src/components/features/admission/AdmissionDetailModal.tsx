"use client";

import { Badge, Button, Modal } from "@/components/ui";
import type { AdmissionApplicationRow } from "@/types";
import AdmissionForm from "./AdmissionForm";
import { ADMISSION_STATUS_TONE, studentName } from "./admission-options";

// Read-only copy of the application form with an "Edit" button that
// loads the record back into the Application tab for changes.

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
            title={application ? studentName(application) || "Application" : ""}
            onClose={onClose}
        >
            {application && (
                <div>
                    <div className="mb-4 flex items-center gap-2">
                        <Badge tone={ADMISSION_STATUS_TONE[application.status]}>
                            {application.status}
                        </Badge>
                        <span className="text-muted-foreground text-xs">
                            Started {application.createdOn}
                        </span>
                    </div>

                    {/* smaller popup: the form scrolls inside instead of growing */}
                    <div className="max-h-[56vh] overflow-y-auto pr-2">
                        <AdmissionForm value={application} readOnly columns="single" />
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
