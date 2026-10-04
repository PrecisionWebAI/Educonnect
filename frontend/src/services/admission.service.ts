import type {
    AdmissionApplicationRow,
    AdmissionFormValues,
    AdmissionStatus,
    SeparationRecord,
} from "@/types";
import { api } from "@/lib/api/client";
import { toCamel, toSnake } from "@/lib/api/case";

// ============================================================
// Operations ▸ Admission service — talks to `admissionapplication`.
//
//   GET  /admissions/applications                    the list (newest first)
//   POST /admissions/applications                    save a draft / register
//   PUT  /admissions/applications/{id}               write the whole form back
//   PUT  /admissions/applications/{id}/separation    record a student leaving
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
        fatherPhone: "",
        fatherEmail: "",
        fatherAnnualIncome: "",
        motherName: "",
        motherOccupation: "",
        motherPhone: "",
        motherEmail: "",
        motherAnnualIncome: "",
        guardianName: "",
        guardianRelation: "",
        guardianPhone: "",
        guardianEmail: "",
        guardianOccupation: "",
        guardianAddress: "",
        appliedForClassLevel: "",
        currentClassOrLastClass: "",
        appliedSectionPreference: "",
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
 * The form's blank state is `""` for every field, but the API stores real
 * types: a blank date input has to travel as `null`, not as an empty string.
 * Keys are converted to the API's snake_case here, once, for both create and
 * update.
 */
function payloadOf(values: AdmissionFormValues): Record<string, unknown> {
    return toSnake<Record<string, unknown>>({
        ...values,
        dateOfBirth: values.dateOfBirth || null,
    });
}

/**
 * Saves the form. `Draft` keeps it editable and half-filled; `Registered` puts
 * the student on the rolls. The server mints the form number (ADM-2026-0148).
 */
export async function createApplication(
    values: AdmissionFormValues,
    status: AdmissionStatus,
): Promise<AdmissionApplicationRow> {
    return toCamel<AdmissionApplicationRow>(
        await api.post("/admissions/applications", { ...payloadOf(values), status }),
    );
}

/** Writes an existing row back (finish a draft, or edit a registered student). */
export async function updateApplication(
    id: number,
    values: AdmissionFormValues,
    status?: AdmissionStatus,
): Promise<AdmissionApplicationRow> {
    const payload = { ...payloadOf(values), ...(status ? { status } : {}) };
    return toCamel<AdmissionApplicationRow>(
        await api.put(`/admissions/applications/${id}`, payload),
    );
}

/** Records why/when a student left; the row then reports as Inactive. */
export async function saveSeparation(
    id: number,
    record: SeparationRecord,
): Promise<AdmissionApplicationRow> {
    return toCamel<AdmissionApplicationRow>(
        await api.put(`/admissions/applications/${id}/separation`, toSnake(record)),
    );
}
