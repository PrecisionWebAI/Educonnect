import type {
    AdmissionApplicationRow,
    AdmissionFormValues,
    AdmissionStats,
    PasswordReset,
    SeparationRecord,
} from "@/types";
import { api } from "@/lib/api/client";
import { toCamel, toSnake } from "@/lib/api/case";

// ============================================================
// Operations ▸ Admission service — talks to `student` (one row per learner).
//
//   GET  /admissions/applications                    the list (newest first)
//   GET  /admissions/stats                           the tiles (counted in SQL)
//   POST /admissions/applications                    admit a student
//   PUT  /admissions/applications/{id}               write the whole form back
//   PUT  /admissions/applications/{id}/separation    record a student leaving
//   POST /admissions/applications/{id}/reset-login   new first-time password
//
// There is no draft. Saving the form **is** the admission: the server mints the
// admission number and creates the student, the guardian (a person row of their
// own), the link between them and the logins the form's own emails make — and
// returns those logins once in `credentials`. A form missing what a student cannot
// be without is refused (`422`) rather than half-stored.
//
// The API answers in snake_case (its schemas are named after the columns) while
// the UI types are camelCase, so payloads cross through `toSnake` / `toCamel`
// instead of a hand-written 40-field mapper that could silently drop a field.
// ============================================================

/** Every form field, blank — seeds spread this and override what's filled. */
export function blankAdmissionForm(): AdmissionFormValues {
    return {
        studentFirstName: "",
        studentMiddleName: "",
        studentLastName: "",
        studentEmail: "",
        dateOfBirth: "",
        gender: "",
        bloodGroup: "",
        religion: "",
        category: "",
        motherTongue: "",
        nationality: "",
        aadhaarId: "",
        address: "",
        permanentAddress: "",
        previousSchoolName: "",
        previousClassPassed: "",
        previousBoard: "",
        transferCertificateNo: "",
        oldUniqueId: "",
        fatherName: "",
        fatherOccupation: "",
        fatherAnnualIncome: "",
        motherName: "",
        motherOccupation: "",
        motherAnnualIncome: "",
        guardianName: "",
        guardianRelation: "",
        guardianPhone: "",
        guardianEmail: "",
        guardianOccupation: "",
        guardianAddress: "",
        appliedForClassLevel: "",
        appliedClassId: "",
        currentClassOrLastClass: "",
        appliedSectionPreference: "",
        appliedSectionId: "",
        needsTransport: "",
        transportRoute: "",
        needsHostel: "",
        notes: "",
    };
}

export async function getAdmissionApplications(): Promise<AdmissionApplicationRow[]> {
    return toCamel<AdmissionApplicationRow[]>(await api.get("/admissions/applications"));
}

/**
 * The Admission screen's tiles, counted by the server for **this school**.
 *
 * Not `getAdmissionApplications().length`: that list is what the table shows, and
 * its size was being used as the roll — so a school bigger than the response cap
 * saw the cap on every tile. `GET /admissions/stats` counts in SQL, inside the same
 * school scope, so the tiles always agree with the table.
 */
export async function getAdmissionStats(): Promise<AdmissionStats> {
    return toCamel<AdmissionStats>(await api.get("/admissions/stats"));
}

/**
 * The form's blank state is an empty string for every field, but the API stores
 * real types: a blank date input has to travel as `null`, not as an empty string,
 * and the same goes for the class/section ids, which are uuids on the server.
 * Keys are converted to the API's snake_case here, once, for both create and
 * update.
 */
function payloadOf(values: AdmissionFormValues): Record<string, unknown> {
    return toSnake<Record<string, unknown>>({
        ...values,
        dateOfBirth: values.dateOfBirth || null,
        appliedClassId: values.appliedClassId || null,
        appliedSectionId: values.appliedSectionId || null,
    });
}

/**
 * Admits a student: the server mints the admission number (`ADM-2026-0148` or the
 * school's own) and creates the student, their guardian and the logins in one go.
 * The response carries those logins with their first-time passwords, once.
 */
export async function createApplication(
    values: AdmissionFormValues,
): Promise<AdmissionApplicationRow> {
    return toCamel<AdmissionApplicationRow>(
        await api.post("/admissions/applications", payloadOf(values)),
    );
}

/**
 * Writes an existing student back. The guardian block in `values` is written to the
 * **person** the child is linked to, so a contact corrected here moves everywhere it
 * is used (their login, their other children's records).
 */
export async function updateApplication(
    id: string,
    values: AdmissionFormValues,
): Promise<AdmissionApplicationRow> {
    return toCamel<AdmissionApplicationRow>(
        await api.put(`/admissions/applications/${id}`, payloadOf(values)),
    );
}

/** Records why/when a student left; the row then reports as Inactive. */
export async function saveSeparation(
    id: string,
    record: SeparationRecord,
): Promise<AdmissionApplicationRow> {
    return toCamel<AdmissionApplicationRow>(
        await api.put(`/admissions/applications/${id}/separation`, toSnake(record)),
    );
}

/**
 * Mints a **new** first-time password for the student's or the guardian's login.
 *
 * The old password stops working immediately. The new one comes back exactly
 * once - only its hash is stored - so it has to be handed over straight away
 * (the screen shows it with a copy button).
 */
export async function resetLoginCredential(
    id: string,
    target: "student" | "guardian",
): Promise<PasswordReset> {
    return toCamel<PasswordReset>(
        await api.post(`/admissions/applications/${id}/reset-login?target=${target}`, {}),
    );
}
