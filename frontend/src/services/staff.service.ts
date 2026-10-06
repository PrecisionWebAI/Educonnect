import type { StaffProfileRow, StaffRegistrationInput, StaffRegistrationRow } from "@/types";
import { api } from "@/lib/api/client";
import { toCamel, toSnake } from "@/lib/api/case";
import { isoInDays } from "@/lib/format";
import { DEPARTMENTS } from "./hiring.service";

// ============================================================
// Operations ▸ Staff Hiring ▸ Registration service — the hire flow.
//
//   GET  /staff/registrations              the registration rows (newest first)
//   POST /staff/registrations              register a hire — creates the login + staff record
//   GET  /staff/profiles                   the Hired tab — one row per staff member
//   POST /staff/profiles/{id}/reset-login  issue a new first-time password
//
// Registering is the whole hiring action: the person gets a login, a
// `staffprofile` row (and a `teacherprofile` row when the post teaches) and an
// employee code (EMP-####). The response carries the login with its one-time
// password — the only moment it is ever visible.
// ============================================================

/** The roles this screen can hire: the catalog minus student/guardian/admin/owner. */
export const STAFF_ROLE_OPTIONS: { value: string; label: string }[] = [
    { value: "teacher", label: "Teacher" },
    { value: "class_teacher", label: "Class Teacher" },
    { value: "subject_teacher", label: "Subject Teacher" },
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

/** Human label for a role codename (`class_teacher` -> `Class Teacher`). */
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
        roleCodename: STAFF_ROLE_OPTIONS[0].value,
        department: STAFF_DEPARTMENTS[0],
        qualification: "",
        experienceYears: 0,
        contactEmail: "",
        joiningDate: isoInDays(0),
        notes: "",
    };
}

/** A fresh first-time password for an existing login. */
export interface StaffPasswordReset {
    fullName: string;
    email: string;
    password: string;
}

export async function getStaffRegistrations(): Promise<StaffRegistrationRow[]> {
    return toCamel<StaffRegistrationRow[]>(await api.get("/staff/registrations"));
}

export async function registerStaff(input: StaffRegistrationInput): Promise<StaffRegistrationRow> {
    return toCamel<StaffRegistrationRow>(await api.post("/staff/registrations", toSnake(input)));
}

export async function getStaffProfiles(): Promise<StaffProfileRow[]> {
    return toCamel<StaffProfileRow[]>(await api.get("/staff/profiles"));
}

export async function resetStaffLogin(profileId: number): Promise<StaffPasswordReset> {
    return toCamel<StaffPasswordReset>(
        await api.post(`/staff/profiles/${profileId}/reset-login`, {}),
    );
}
