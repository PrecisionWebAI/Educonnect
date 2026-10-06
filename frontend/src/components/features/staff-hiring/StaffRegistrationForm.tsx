"use client";

import { Button, Card, Input, Select } from "@/components/ui";
import { STAFF_DEPARTMENTS, STAFF_ROLE_OPTIONS } from "@/services";
import type { StaffRegistrationInput } from "@/types";

// The short hire form on the Registration tab - this is where a hire starts
// now, not in the candidate pipeline.
//
// Submitting it is the whole hiring action: the server creates the login
// (`tea.*` for teaching posts, `stf.*` for the rest), the staff record and the
// employee code in one step, so "registered" and "on the staff roll" can never
// drift apart.

export default function StaffRegistrationForm({
    value,
    onChange,
    onSubmit,
}: {
    value: StaffRegistrationInput;
    onChange: (value: StaffRegistrationInput) => void;
    onSubmit: () => void;
}) {
    return (
        <Card title="Register a hire">
            <div className="grid grid-cols-1 gap-x-4 gap-y-5 pt-2 md:grid-cols-2">
                <Input
                    label="Full name"
                    value={value.fullName}
                    onChange={(e) => onChange({ ...value, fullName: e.target.value })}
                />
                <Select
                    label="Post (role)"
                    value={value.roleCodename}
                    onChange={(e) => onChange({ ...value, roleCodename: e.target.value })}
                >
                    {STAFF_ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Department"
                    value={value.department}
                    onChange={(e) => onChange({ ...value, department: e.target.value })}
                >
                    {STAFF_DEPARTMENTS.map((department) => (
                        <option key={department} value={department}>
                            {department}
                        </option>
                    ))}
                </Select>
                <Input
                    label="Highest qualification"
                    value={value.qualification}
                    onChange={(e) => onChange({ ...value, qualification: e.target.value })}
                />
                <Input
                    label="Experience (years)"
                    type="number"
                    min={0}
                    value={String(value.experienceYears)}
                    onChange={(e) =>
                        onChange({ ...value, experienceYears: Number(e.target.value) || 0 })
                    }
                />
                <Input
                    label="Contact email"
                    type="email"
                    value={value.contactEmail}
                    onChange={(e) => onChange({ ...value, contactEmail: e.target.value })}
                />
                <Input
                    label="Joining date"
                    type="date"
                    value={value.joiningDate}
                    onChange={(e) => onChange({ ...value, joiningDate: e.target.value })}
                />
                <div className="flex items-end">
                    <Button variant="primary" onClick={onSubmit}>
                        Register & create login
                    </Button>
                </div>
            </div>
            <p className="text-muted-foreground pt-4 text-sm">
                Registering creates the login and the staff record straight away, so the person
                shows up on the Hired tab (and can be paid from the salary register) without a
                second step.
            </p>
        </Card>
    );
}
