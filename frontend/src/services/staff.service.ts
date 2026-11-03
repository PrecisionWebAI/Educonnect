import type { StaffProfileCreateResult, StaffProfileRow, StaffRegistrationInput } from "@/types";
import { api } from "@/lib/api/client";
import { toCamel, toSnake } from "@/lib/api/case";
import { isoInDays } from "@/lib/format";
import { DEPARTMENTS } from "./hiring.service";

// ============================================================
// Operations ▸ Staff Hiring ▸ hire service — the employee flow.
//
//   POST /staff/profiles                   fill the hire form — creates the login + employee
//   GET  /staff/profiles                   the Hired tab — one row per employee
//   POST /staff/profiles/{id}/reset-login  issue a new first-time password
//
// Filling the form is the whole hiring action: the person gets a login, an
// `employee` row and an employee code (EMP-####). The response carries the
// login with its one-time password — the only moment it is ever visible.
// ============================================================

/** The roles this screen can hire: the catalog minus student/guardian/admins. */
export const STAFF_ROLE_OPTIONS: { value: string; label: string }[] = [
    { value: "teacher", label: "Teacher" },
    { value: "hod", label: "Head of Department" },
    { value: "vice_principal", label: "Vice Principal" },
    { value: "principal", label: "Principal" },
    { value: "accountant", label: "Accountant" },
    { value: "librarian", label: "Librarian" },
    { value: "transport", label: "Transport" },
    { value: "staff", label: "Office / Support Staff" },
];

/** Departments a hire can be filed under (the hiring list, plus the offices). */
export const STAFF_DEPARTMENTS = [...DEPARTMENTS, "Accounts", "Library", "Transport", "Support"];

/** Human label for a role codename (`teacher` -> `Teacher`). */
export function staffRoleLabel(codename: string): string {
    const match = STAFF_ROLE_OPTIONS.find((option) => option.value === codename);
    if (match) return match.label;
    return codename
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

/** An empty registration form, dated today. */
export function blankStaffRegistration(): StaffRegistrationInput {
    return {
        fullName: "",
        roleCodenames: [STAFF_ROLE_OPTIONS[0].value],
        department: STAFF_DEPARTMENTS[0],
        qualification: "",
        experienceYears: 0,
        contactEmail: "",
        joiningDate: isoInDays(0),
        candidateId: null,
        phone: "",
        subjectIds: [],
        address: "",
        emergencyContact: "",
        aadhaarNo: "",
        panNo: "",
        bankName: "",
        bankAccountNo: "",
        ifsc: "",
        salaryMonthly: null,
        previousEmployerMonthlySalary: null,
    };
}

/** A fresh first-time password for an existing login. */
export interface StaffPasswordReset {
    fullName: string;
    email: string;
    password: string;
}

export async function registerStaff(input: StaffRegistrationInput): Promise<StaffProfileCreateResult> {
    return toCamel<StaffProfileCreateResult>(await api.post("/staff/profiles", toSnake(input)));
}

export async function updateStaffProfile(
    profileId: string,
    input: StaffRegistrationInput,
): Promise<StaffProfileRow> {
    return toCamel<StaffProfileRow>(await api.put(`/staff/profiles/${profileId}`, toSnake(input)));
}

export async function getStaffProfiles(): Promise<StaffProfileRow[]> {
    return toCamel<StaffProfileRow[]>(await api.get("/staff/profiles"));
}

export async function resetStaffLogin(profileId: string): Promise<StaffPasswordReset> {
    return toCamel<StaffPasswordReset>(
        await api.post(`/staff/profiles/${profileId}/reset-login`, {}),
    );
}

/** Remove a hired employee and the login the hire created. */
export async function deleteStaffProfile(profileId: string): Promise<void> {
    await api.delete(`/staff/profiles/${profileId}`);
}
