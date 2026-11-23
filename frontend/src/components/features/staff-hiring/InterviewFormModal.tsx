"use client";

import { Button, Input, Modal, Select, Textarea } from "@/components/ui";
import { STAFF_DEPARTMENTS, STAFF_ROLE_OPTIONS } from "@/services";
import type { CandidateDraft } from "./useStaffHiring";

// Interview scheduling form — replaces the old "New Candidate" CV intake. It
// captures the person (name, phone, email, qualification), the post applied for
// (a role codename), the subject, experience and the interview slot, plus an
// optional resume upload.

export default function InterviewFormModal({
    open,
    draft,
    suggestions,
    onChange,
    onClose,
    onSubmit,
}: {
    open: boolean;
    draft: CandidateDraft;
    /** Subject names offered as suggestions; the field still takes any text. */
    suggestions: string[];
    onChange: (draft: CandidateDraft) => void;
    onClose: () => void;
    onSubmit: () => void;
}) {
    return (
        <Modal open={open} title="Schedule Interview" onClose={onClose}>
            <div className="space-y-4">
                <Input
                    label="Candidate name"
                    value={draft.candidateName}
                    onChange={(e) => onChange({ ...draft, candidateName: e.target.value })}
                />
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Input
                        label="Phone"
                        value={draft.phone}
                        onChange={(e) => onChange({ ...draft, phone: e.target.value })}
                    />
                    <Input
                        label="Email"
                        type="email"
                        value={draft.email}
                        onChange={(e) => onChange({ ...draft, email: e.target.value })}
                    />
                </div>
                <Select
                    label="Applied For"
                    value={draft.appliedFor}
                    onChange={(e) => onChange({ ...draft, appliedFor: e.target.value })}
                >
                    {STAFF_ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </Select>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                        <Input
                            label="Subject"
                            list="interview-subject-suggestions"
                            value={draft.subjectName}
                            onChange={(e) => onChange({ ...draft, subjectName: e.target.value })}
                            placeholder="Any subject — suggestions are optional"
                        />
                        <datalist id="interview-subject-suggestions">
                            {suggestions.map((name) => (
                                <option key={name} value={name} />
                            ))}
                        </datalist>
                    </div>
                    <Select
                        label="Department"
                        value={draft.department}
                        onChange={(e) => onChange({ ...draft, department: e.target.value })}
                    >
                        {STAFF_DEPARTMENTS.map((department) => (
                            <option key={department} value={department}>
                                {department}
                            </option>
                        ))}
                    </Select>
                </div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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
                        onChange={(e) =>
                            onChange({ ...draft, experience: Number(e.target.value) || 0 })
                        }
                    />
                </div>
                <Input
                    label="Interview date & time"
                    type="datetime-local"
                    value={draft.interviewAt}
                    onChange={(e) => onChange({ ...draft, interviewAt: e.target.value })}
                />
                <Textarea
                    label="Interview note (optional)"
                    value={draft.interviewNote}
                    onChange={(e) => onChange({ ...draft, interviewNote: e.target.value })}
                />
                <Input
                    label="Resume (PDF / Word / image)"
                    type="file"
                    accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                    onChange={(e) =>
                        onChange({ ...draft, resumeFile: e.target.files?.[0] ?? null })
                    }
                />
                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={onSubmit}>
                        Schedule Interview
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
