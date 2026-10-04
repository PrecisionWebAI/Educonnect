"use client";

import { Button, Input, Modal, Select } from "@/components/ui";
import { DEPARTMENTS, DESIGNATIONS } from "@/services";
import type { CandidateDraft } from "./useStaffHiring";

// New candidate / CV intake form.

export default function CandidateFormModal({
    open,
    draft,
    onChange,
    onClose,
    onSubmit,
}: {
    open: boolean;
    draft: CandidateDraft;
    onChange: (draft: CandidateDraft) => void;
    onClose: () => void;
    onSubmit: () => void;
}) {
    return (
        <Modal open={open} title="New Candidate" onClose={onClose}>
            <div className="space-y-4">
                <Input
                    label="Candidate name"
                    value={draft.candidateName}
                    onChange={(e) => onChange({ ...draft, candidateName: e.target.value })}
                />
                <Select
                    label="Vacancy"
                    value={draft.role}
                    onChange={(e) => onChange({ ...draft, role: e.target.value })}
                >
                    {DESIGNATIONS.map((d) => (
                        <option key={d} value={d}>
                            {d}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Department"
                    value={draft.department}
                    onChange={(e) => onChange({ ...draft, department: e.target.value })}
                >
                    {DEPARTMENTS.map((d) => (
                        <option key={d} value={d}>
                            {d}
                        </option>
                    ))}
                </Select>
                <Input
                    label="Highest qualification"
                    value={draft.qualification}
                    onChange={(e) => onChange({ ...draft, qualification: e.target.value })}
                />
                <Input
                    label="Experience (years)"
                    type="number"
                    min={0}
                    value={String(draft.experience)}
                    onChange={(e) => onChange({ ...draft, experience: Number(e.target.value) || 0 })}
                />
                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={onSubmit}>
                        Add Candidate
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
