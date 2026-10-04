// ============================================================
// Grade/class catalog shared by the admission + fees pages.
//
// These names mirror the `gradeclass` rows the backend seeds
// ("Grade 6" … "Grade 10"), not a prettier UI wording: the value a form sends
// has to resolve to a real class, and the API matches it against
// `gradeclass.name` before falling back to the level number.
// ============================================================

export const GRADE_NAMES = [
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

/** Class filter dropdown — "All Classes" means "do not narrow". */
export const CLASS_OPTIONS = ["All Classes", ...GRADE_NAMES];

/** Sections a student can be placed in (`section.name`). */
export const SECTION_OPTIONS = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
];

/** School stage per class, mirroring `classroom.stage`. */
export const CLASS_STAGE: Record<string, string> = {
    Nursery: "pre_primary",
    LKG: "pre_primary",
    UKG: "pre_primary",
    "Class 1": "primary",
    "Class 2": "primary",
    "Class 3": "primary",
    "Class 4": "primary",
    "Class 5": "primary",
    "Class 6": "middle",
    "Class 7": "middle",
    "Class 8": "middle",
    "Class 9": "secondary",
    "Class 10": "secondary",
    "Class 11": "senior_secondary",
    "Class 12": "senior_secondary",
};

/** Class list without the "All Classes" filter entry. */
export const CLASS_NAMES = GRADE_NAMES;
