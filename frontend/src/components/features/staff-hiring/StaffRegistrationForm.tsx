"use client";

import { Button, Card, Input, Label, Select } from "@/components/ui";
import { STAFF_DEPARTMENTS, STAFF_ROLE_OPTIONS } from "@/services";
import type { StaffRegistrationInput, SubjectRow } from "@/types";

/** Add or remove one value, keeping the pick order. */
function toggle<T>(current: T[], value: T): T[] {
    return current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value];
}

export default function StaffRegistrationForm({
    value,
    subjects,
    onChange,
    onSubmit,
    onCancel,
}: {
    value: StaffRegistrationInput;
    subjects: SubjectRow[];
    onChange: (value: StaffRegistrationInput) => void;
    onSubmit: () => void;
    onCancel: () => void;
}) {
    return (
        <Card title="Register a hire">
            <div className="grid grid-cols-1 gap-x-4 gap-y-5 pt-2 md:grid-cols-2">
                <Input
                    label="Full name"
                    value={value.fullName}
                    onChange={(e) => onChange({ ...value, fullName: e.target.value })}
                />
                <div className="md:col-span-2">
                    <Label>Roles (pick one or more)</Label>
                    <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 rounded-md border p-3">
                        {STAFF_ROLE_OPTIONS.map((option) => (
                            <label
                                key={option.value}
                                className="flex items-center gap-2 text-sm"
                            >
                                <input
                                    type="checkbox"
                                    checked={value.roleCodenames.includes(option.value)}
                                    onChange={() =>
                                        onChange({
                                            ...value,
                                            roleCodenames: toggle(
                                                value.roleCodenames,
                                                option.value,
                                            ),
                                        })
                                    }
                                />
                                {option.label}
                            </label>
                        ))}
                    </div>
                    <p className="text-muted-foreground pt-1 text-xs">
                        The first role picked is the primary one — its dashboard opens at login.
                        A person may hold several (a principal who also teaches).
                    </p>
                </div>
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
                <div className="md:col-span-2">
                    <Label>Subjects (pick one or more)</Label>
                    <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 rounded-md border p-3">
                        {subjects.length === 0 ? (
                            <span className="text-muted-foreground text-sm">
                                No subjects yet for this school.
                            </span>
                        ) : (
                            subjects.map((subject) => (
                                <label
                                    key={subject.id}
                                    className="flex items-center gap-2 text-sm"
                                >
                                    <input
                                        type="checkbox"
                                        checked={value.subjectIds.includes(subject.id)}
                                        onChange={() =>
                                            onChange({
                                                ...value,
                                                subjectIds: toggle(
                                                    value.subjectIds,
                                                    subject.id,
                                                ),
                                            })
                                        }
                                    />
                                    {subject.name}
                                </label>
                            ))
                        )}
                    </div>
                </div>
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
                <Input
                    label="Phone"
                    value={value.phone}
                    onChange={(e) => onChange({ ...value, phone: e.target.value })}
                />
                <Input
                    label="Emergency contact"
                    value={value.emergencyContact}
                    onChange={(e) => onChange({ ...value, emergencyContact: e.target.value })}
                />
                <Input
                    label="Address"
                    value={value.address}
                    onChange={(e) => onChange({ ...value, address: e.target.value })}
                />

                <div className="md:col-span-2 border-t pt-1 text-sm font-medium text-muted-foreground">
                    KYC &amp; payroll
                </div>

                <Input
                    label="Aadhaar number *"
                    value={value.aadhaarNo}
                    onChange={(e) => onChange({ ...value, aadhaarNo: e.target.value })}
                />
                <Input
                    label="PAN (optional)"
                    value={value.panNo}
                    onChange={(e) => onChange({ ...value, panNo: e.target.value })}
                />
                <Input
                    label="Bank name"
                    value={value.bankName}
                    onChange={(e) => onChange({ ...value, bankName: e.target.value })}
                />
                <Input
                    label="Bank account number *"
                    value={value.bankAccountNo}
                    onChange={(e) => onChange({ ...value, bankAccountNo: e.target.value })}
                />
                <Input
                    label="IFSC code *"
                    value={value.ifsc}
                    onChange={(e) => onChange({ ...value, ifsc: e.target.value })}
                />
                <Input
                    label="Monthly salary (₹) *"
                    type="number"
                    min={0}
                    value={value.salaryMonthly ?? ""}
                    onChange={(e) =>
                        onChange({
                            ...value,
                            salaryMonthly: e.target.value ? Number(e.target.value) : null,
                        })
                    }
                />
                <Input
                    label="Previous monthly salary (₹)"
                    type="number"
                    min={0}
                    value={value.previousEmployerMonthlySalary ?? ""}
                    onChange={(e) =>
                        onChange({
                            ...value,
                            previousEmployerMonthlySalary: e.target.value ? Number(e.target.value) : null,
                        })
                    }
                />

                <div className="flex items-end md:col-span-2 gap-2">
                    <Button variant="outline" onClick={onCancel}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={onSubmit}>
                        Register &amp; create login
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
