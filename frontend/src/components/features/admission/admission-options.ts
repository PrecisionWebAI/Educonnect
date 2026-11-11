import type {
    AdmissionApplicationRow,
    AdmissionFormValues,
    AdmissionStudentStatus,
    SeparationSession,
} from "@/types";

// ============================================================
// Admission — form definition + option lists + table helpers.
//
// The form is declarative: `ADMISSION_FORM_SECTIONS` mirrors the
// ADMISSION FORM -> DATABASE block of db_mapping.txt
// (`student`), and the same config renders the editable form, the
// read-only view and the filter dropdowns.
// ============================================================

export const GENDER_OPTIONS = ["Male", "Female", "Other"];
export const BLOOD_GROUP_OPTIONS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
export const CATEGORY_OPTIONS = ["General", "OBC", "SC", "ST", "EWS", "Other"];

/**
 * Religion, as a **dropdown** like Blood group - the office picks instead of
 * typing, so one value cannot be spelled three ways. "Other" is a real answer:
 * the list is the common ones, not the only ones.
 */
export const RELIGION_OPTIONS = [
    "Hindu",
    "Muslim",
    "Christian",
    "Sikh",
    "Buddhist",
    "Jain",
    "Parsi",
    "Jewish",
    "Other",
];

/** Mother tongue, as a dropdown like Blood group (with "Other"). */
export const MOTHER_TONGUE_OPTIONS = [
    "Hindi",
    "English",
    "Bengali",
    "Marathi",
    "Telugu",
    "Tamil",
    "Gujarati",
    "Urdu",
    "Kannada",
    "Odia",
    "Malayalam",
    "Punjabi",
    "Assamese",
    "Maithili",
    "Sanskrit",
    "Other",
];
export const RELATION_OPTIONS = [
    "Father",
    "Mother",
    "Uncle",
    "Aunt",
    "Grandparent",
    "Legal Guardian",
];
export const YES_NO_OPTIONS = ["Yes", "No"];
export const BOARD_OPTIONS = ["CBSE", "ICSE", "State Board", "IB", "IGCSE", "Other"];

/**
 * Classes the admission form offers, in school order: Nursery, LKG, UKG, then
 * Class 1 to Class 12.
 *
 * A plain list like `GENDER_OPTIONS`, because the "Class Register" block asks one
 * simple question - which class the family is applying for - and the office reads
 * the answer back as the name the class is called by ("Class 6"). `find_classroom`
 * on the server resolves that name to one of the school's classes when the form is
 * registered.
 */
export const CLASS_OPTIONS = [
    "Nursery",
    "LKG",
    "UKG",
    "Class 1",
    "Class 2",
    "Class 3",
    "Class 4",
    "Class 5",
    "Class 6",
    "Class 7",
    "Class 8",
    "Class 9",
    "Class 10",
    "Class 11",
    "Class 12",
];

/** A class runs sections A to J; the family states which one it prefers. */
export const SECTION_OPTIONS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"];

/** Occupation list shared by the father / mother / guardian blocks. */
export const OCCUPATION_OPTIONS = [
    "Business",
    "Government Service",
    "Private Service",
    "Self Employed",
    "Professional",
    "Farmer",
    "Retired",
    "Homemaker",
    "Others",
];

/** Annual-income bands (father / mother). */
export const INCOME_RANGE_OPTIONS = [
    "0 – 5L",
    "5L – 10L",
    "10L – 15L",
    "15L – 20L",
    "20L +",
];

/** Why the student left the school — used by the Separation form. */
export const SEPARATION_REASON_OPTIONS = [
    "Rusticated",
    "Transfer Certificate Issued",
    "Long Absence",
    "Fee Default",
    "Disciplinary Action",
    "Parent Request",
    "Relocation",
    "Others",
];

export const SEPARATION_SESSION_OPTIONS = ["Completed Session", "Incomplete Session"];

export interface AdmissionFieldDef {
    key: keyof AdmissionFormValues;
    label: string;
    type?: "text" | "email" | "date" | "number" | "textarea";
    options?: readonly string[];
    /**
     * A mandatory field: its label carries a `*` and the save refuses without it
     * (see `missingRequiredFields`, which mirrors the server's rule).
     *
     * There is no draft to finish later, so a mandatory field is what a student
     * cannot be without - the form is saved once, complete.
     */
    required?: boolean;
}

export interface AdmissionFormSection {
    title: string;
    fields: AdmissionFieldDef[];
}

/** The whole admission form, section by section. */
export const ADMISSION_FORM_SECTIONS: AdmissionFormSection[] = [
    // Class Register comes first on purpose: the form opens with the question it
    // exists to answer - which class-section the family is applying for - and the
    // student's own details follow it.
    {
        title: "Class Register",
        fields: [
            // Two plain dropdowns, like Gender and Blood group: the class list
            // runs Nursery ... Class 12 and the section list runs A ... J, so the
            // office picks the class-section instead of typing it in.
            { key: "appliedForClassLevel", label: "Class", options: CLASS_OPTIONS, required: true },
            {
                key: "appliedSectionPreference",
                label: "Section Preference",
                options: SECTION_OPTIONS,
            },
        ],
    },
    {
        title: "Student",
        fields: [
            { key: "studentFirstName", label: "First name", required: true },
            { key: "studentMiddleName", label: "Middle name" },
            { key: "studentLastName", label: "Last name" },
            { key: "studentEmail", label: "Email", type: "email" },
            { key: "dateOfBirth", label: "Date of birth", type: "date" },
            { key: "gender", label: "Gender", options: GENDER_OPTIONS },
            { key: "bloodGroup", label: "Blood group", options: BLOOD_GROUP_OPTIONS },
            { key: "religion", label: "Religion", options: RELIGION_OPTIONS },
            { key: "category", label: "Category", options: CATEGORY_OPTIONS },
            { key: "motherTongue", label: "Mother tongue", options: MOTHER_TONGUE_OPTIONS },
            { key: "nationality", label: "Nationality" },
            { key: "aadhaarId", label: "Aadhaar ID" },
            { key: "address", label: "Address", type: "textarea" },
            { key: "permanentAddress", label: "Permanent address", type: "textarea" },
        ],
    },
    {
        title: "Previous School",
        fields: [
            { key: "previousSchoolName", label: "Previous school name" },
            { key: "previousClassPassed", label: "Last class passed" },
            { key: "previousBoard", label: "Board", options: BOARD_OPTIONS },
            { key: "transferCertificateNo", label: "Transfer certificate no" },
            { key: "oldUniqueId", label: "Unique ID" },
        ],
    },
    {
        // Family detail only: a phone or an email typed for a parent would be a
        // *contact*, and the product keeps one per person - the GUARDIAN block below.
        title: "Father (family detail)",
        fields: [
            { key: "fatherName", label: "Name" },
            { key: "fatherOccupation", label: "Occupation", options: OCCUPATION_OPTIONS },
            { key: "fatherAnnualIncome", label: "Annual income", options: INCOME_RANGE_OPTIONS },
        ],
    },
    {
        title: "Mother (family detail)",
        fields: [
            { key: "motherName", label: "Name" },
            { key: "motherOccupation", label: "Occupation", options: OCCUPATION_OPTIONS },
            { key: "motherAnnualIncome", label: "Annual income", options: INCOME_RANGE_OPTIONS },
        ],
    },
    {
        title: "Guardian (the family's contact)",
        fields: [
            { key: "guardianName", label: "Name", required: true },
            { key: "guardianRelation", label: "Relation", options: RELATION_OPTIONS },
            { key: "guardianPhone", label: "Phone", required: true },
            { key: "guardianEmail", label: "Email", type: "email", required: true },
            { key: "guardianOccupation", label: "Occupation", options: OCCUPATION_OPTIONS },
            { key: "guardianAddress", label: "Address", type: "textarea" },
        ],
    },
    {
        title: "Logistics",
        fields: [
            { key: "needsTransport", label: "Needs transport", options: YES_NO_OPTIONS },
            { key: "transportRoute", label: "Transport route" },
            { key: "needsHostel", label: "Needs hostel", options: YES_NO_OPTIONS },
            { key: "notes", label: "Notes", type: "textarea" },
        ],
    },
];

// ---------- Mandatory fields ----------

/**
 * What a form cannot be saved without: a label plus the field that satisfies it.
 *
 * The **guardian block is the only contact block**: the email the family signs in
 * with and the phone the school rings them on come from there, so the father /
 * mother blocks are family detail and carry no contact of their own. This mirrors
 * `REQUIRED_TO_ADMIT` on the server, which is the real gate; this copy exists so the
 * office is told before the round-trip.
 *
 * Two fields are deliberately absent: the student's own **email** (a child without
 * one has no login of their own - the guardian's account is the family's way in)
 * and the student's **last name** (many children have a single name).
 */
const REQUIRED_FIELDS: { label: string; keys: (keyof AdmissionFormValues)[] }[] = [
    { label: "First name", keys: ["studentFirstName"] },
    { label: "Class", keys: ["appliedForClassLevel"] },
    { label: "Guardian name", keys: ["guardianName"] },
    { label: "Guardian email", keys: ["guardianEmail"] },
    { label: "Guardian phone", keys: ["guardianPhone"] },
];

/** The mandatory labels still empty on this form, in form order ([] when ready). */
export function missingRequiredFields(values: AdmissionFormValues): string[] {
    return REQUIRED_FIELDS.filter(
        (entry) => !entry.keys.some((key) => (values[key] ?? "").trim()),
    ).map((entry) => entry.label);
}

// ---------- Derived display values ----------

/** The guardian shown in the tables - the family's contact, from the person row. */
export function primaryGuardian(row: AdmissionApplicationRow): string {
    return row.guardianName || "—";
}

/** The family's phone number — used for the "Phone number" filter. */
export function phoneNumbers(row: AdmissionApplicationRow): string {
    return row.guardianPhone || "";
}

/** The family's email address — used for the "Email" filter. */
export function emailAddresses(row: AdmissionApplicationRow): string {
    return row.guardianEmail || "";
}

/** Contact column shown in the students table. */
export function primaryPhone(row: AdmissionApplicationRow): string {
    return row.guardianPhone || "—";
}

/** Contact column shown in the students table. */
export function primaryEmail(row: AdmissionApplicationRow): string {
    return row.guardianEmail || "—";
}

/** "Aarav Sharma" (middle name included when present). */
export function studentName(values: AdmissionFormValues): string {
    return [values.studentFirstName, values.studentMiddleName, values.studentLastName]
        .filter(Boolean)
        .join(" ");
}

// ---------- Filters ----------
// Each filter is a field dropdown + a value box, matching on the row.

export interface AdmissionFilterField {
    value: string;
    label: string;
    get: (row: AdmissionApplicationRow) => string;
}

export const STUDENT_FILTER_FIELDS: AdmissionFilterField[] = [
    { value: "student", label: "Student name", get: studentName },
    { value: "admissionNumber", label: "Admission number", get: (r) => r.admissionNumber },
    { value: "guardian", label: "Guardian name", get: primaryGuardian },
    { value: "class", label: "Class", get: (r) => r.appliedForClassLevel },
    { value: "section", label: "Section", get: (r) => r.appliedSectionPreference },
    { value: "phone", label: "Phone number", get: phoneNumbers },
    { value: "email", label: "Email", get: emailAddresses },
];

/** Keeps the rows whose selected field contains the typed value. */
export function filterApplications(
    rows: AdmissionApplicationRow[],
    fields: AdmissionFilterField[],
    field: string,
    value: string,
): AdmissionApplicationRow[] {
    const q = value.trim().toLowerCase();
    if (!q) return rows;
    const fieldDef = fields.find((f) => f.value === field) ?? fields[0];
    return rows.filter((row) => fieldDef.get(row).toLowerCase().includes(q));
}

// ---------- Student status (derived from the separation record) ----------
/** A student is Inactive once a separation has been recorded. */
export function studentStatus(row: AdmissionApplicationRow): AdmissionStudentStatus {
    return row.separation ? "Inactive" : "Active";
}

/** Class the student was in when they left (falls back to the form values). */
export function droppedClassOf(row: AdmissionApplicationRow): string {
    return row.separation?.droppedClass || row.currentClassOrLastClass || row.appliedForClassLevel;
}

export interface StudentFilters {
    field: string;
    value: string;
    status: AdmissionStudentStatus | "All";
    reason: string;
    session: SeparationSession | "All";
}

/**
 * Student-list filtering: the field/value pair plus the separation controls
 * (status, reason, completed / incomplete session). A child who has left is still
 * in the list - that is what the status filter is for - because leaving the roll is
 * not the same as being deleted.
 */
export function filterStudents(
    rows: AdmissionApplicationRow[],
    filters: StudentFilters,
): AdmissionApplicationRow[] {
    const q = filters.value.trim().toLowerCase();
    const fieldDef =
        STUDENT_FILTER_FIELDS.find((f) => f.value === filters.field) ??
        STUDENT_FILTER_FIELDS[0];
    const reason = filters.reason.trim().toLowerCase();

    return rows.filter((row) => {
        if (q && !fieldDef.get(row).toLowerCase().includes(q)) return false;
        if (filters.status !== "All" && studentStatus(row) !== filters.status) return false;
        if (reason && !(row.separation?.reason ?? "").toLowerCase().includes(reason)) return false;
        if (filters.session !== "All" && row.separation?.session !== filters.session) return false;
        return true;
    });
}
