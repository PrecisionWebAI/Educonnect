// ============================================================
// Grade/class catalog shared by the admission + fees pages.
//
// These names mirror the `gradeclass` rows the backend seeds
// ("Grade 6" … "Grade 10"), not a prettier UI wording: the value a form sends
// has to resolve to a real class, and the API matches it against
// `gradeclass.name` before falling back to the level number.
// ============================================================

export const GRADE_NAMES = [
    "Grade 6",
    "Grade 7",
    "Grade 8",
    "Grade 9",
    "Grade 10",
];

/** Class filter dropdown — "All Classes" means "do not narrow". */
export const CLASS_OPTIONS = ["All Classes", ...GRADE_NAMES];

/** Sections a student can be placed in (`section.name`). */
export const SECTION_OPTIONS = ["A", "B", "C", "D"];

/** Class list without the "All Classes" filter entry. */
export const CLASS_NAMES = GRADE_NAMES;
