// ============================================================
// Grade/class catalog shared by the admission + fees pages.
// Mirrors `gradeclass` name values seeded on the backend.
// ============================================================

export const CLASS_OPTIONS = [
    "All Classes",
    "Class 6",
    "Class 7",
    "Class 8",
    "Class 9",
    "Class 10",
    "Class 11",
    "Class 12",
];

/** Sections a student can be placed in (`section.name`). */
export const SECTION_OPTIONS = ["A", "B", "C", "D"];

/** Class list without the "All Classes" filter entry. */
export const CLASS_NAMES = CLASS_OPTIONS.filter((c) => c !== "All Classes");
