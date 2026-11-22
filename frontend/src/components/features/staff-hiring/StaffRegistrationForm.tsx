"use client";

import { Button, Card, Input, MultiSelect, Select } from "@/components/ui";
import { STAFF_DEPARTMENTS, STAFF_ROLE_OPTIONS } from "@/services";
import type { StaffRegistrationInput } from "@/types";

export default function StaffRegistrationForm({
    value,
    suggestions,
    onChange,
    onSubmit,
    onCancel,
}: {
    value: StaffRegistrationInput;
    /** Subject names offered as suggestions; the field still takes any text. */
    suggestions: string[];
    onChange: (value: StaffRegistrationInput) => void;
    onSubmit: () => void;
    onCancel: () => void;
}) {
    return (
        <Card title="Register an Employee">
            <div className="grid grid-cols-1 gap-x-4 gap-y-5 pt-2 md:grid-cols-2">
                <Input
                    label="Full name *"
                    value={value.fullName}
                    onChange={(e) => onChange({ ...value, fullName: e.target.value })}
                />
                <MultiSelect
                    label="Roles *"
                    options={STAFF_ROLE_OPTIONS}
                    value={value.roleCodenames}
                    onChange={(roleCodenames) => onChange({ ...value, roleCodenames })}
                />
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
                    label="Subjects they can teach"
                    list="staff-subject-suggestions"
                    value={value.subjectTags}
                    onChange={(e) => onChange({ ...value, subjectTags: e.target.value })}
                    placeholder="e.g. English, Maths — informational only"
                />
                <datalist id="staff-subject-suggestions">
                    {suggestions.map((name) => (
                        <option key={name} value={name} />
                    ))}
                </datalist>
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
                    label="Contact email *"
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
                    label="Phone *"
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

                <div className="text-muted-foreground border-t pt-1 text-sm font-medium md:col-span-2">
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
                    label="Bank name *"
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
                            previousEmployerMonthlySalary: e.target.value
                                ? Number(e.target.value)
                                : null,
                        })
                    }
                />

                <div className="flex items-end gap-2 md:col-span-2">
                    <Button variant="outline" onClick={onCancel}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={onSubmit}>
                        Register &amp; create login
                    </Button>
                </div>
            </div>
        </Card>
    );
}
