"use client";

// ============================================================
// useSourceMaster — saved "sources with details" library
// (blueprint §1.2 addendum). Entries persist to localStorage so
// a class → subject → chapter chain survives reloads and feeds
// the Basics step's cascading dropdowns:
//   select Class → Subject options = subjects saved for it
//   select Subject → Chapter options = chapters saved for it
// ============================================================

import { useCallback, useState } from "react";

export interface SavedResource {
    id: string;
    /** A=PDF · B=image · C=URL · D=pasted text · E=bank */
    type: "A" | "B" | "C" | "D" | "E";
    /** teacher-given name, e.g. "Microorganisms NCERT PDF" */
    name: string;
    chapter: string;
    fileName?: string;
    fileSize?: string;
    pages?: string;
    url?: string;
    textExcerpt?: string;
    bankRef?: string;
    teacherName?: string;
    createdAt: string;
}

export interface SavedChapter {
    name: string;
    subChapters: string[];
}

export interface SavedSourceDetail {
    id: string;
    className: string;
    subject: string;
    board: string;
    chapters: SavedChapter[];
    /** per-chapter saved resource items (PDF / image / URL / text / bank) */
    resources: SavedResource[];
}

const STORAGE_KEY = "eduverse.saved-source-details.v1";

function seedDefaults(): SavedSourceDetail[] {
    const at = new Date().toISOString();
    const res = (
        className: string,
        chapter: string,
        items: Omit<SavedResource, "id" | "chapter" | "createdAt">[],
    ): SavedResource[] =>
        items.map((r, i) => ({
            ...r,
            id: `seed-${className}-${chapter}-${i}`,
            chapter,
            createdAt: at,
        }));
    return [
        {
            id: "srcseed8science",
            className: "8",
            subject: "Science",
            board: "CBSE",
            chapters: [
                { name: "Crop Production", subChapters: ["Agriculture basics", "Irrigation"] },
                { name: "Microorganisms", subChapters: ["Friend & foe", "Diseases"] },
                { name: "Force & Pressure", subChapters: ["Contact forces", "Pressure"] },
            ],
            resources: [
                ...res("8", "Crop Production", [
                    { type: "A", name: "Crop Production NCERT PDF", fileName: "crop-production-ncert.pdf", fileSize: "3.1 MB", pages: "1–24", teacherName: "NCERT" },
                    { type: "A", name: "Crop Production worksheet", fileName: "crop-production-ws.pdf", fileSize: "0.6 MB" },
                    { type: "C", name: "Crop types web page", url: "https://ncert.example/crop" },
                    { type: "D", name: "Crop Production summary notes", textExcerpt: "Crops are plants of the same kind grown on a large scale for food, fodder or other use…" },
                ]),
                ...res("8", "Microorganisms", [
                    { type: "A", name: "Microorganisms NCERT PDF", fileName: "ncert-ch2-microorganisms.pdf", fileSize: "2.4 MB", pages: "12–28", teacherName: "NCERT" },
                    { type: "B", name: "Microscope diagram photo", fileName: "microscope-diagram.jpg", fileSize: "1.1 MB" },
                    { type: "C", name: "NCERT chapter page", url: "https://ncert.example/ch2" },
                    { type: "D", name: "Teacher summary notes", textExcerpt: "Microorganisms are too small to be seen with naked eyes…" },
                ]),
                ...res("8", "Force & Pressure", [
                    { type: "A", name: "Force & Pressure worksheet", fileName: "force-pressure-ws.pdf", fileSize: "0.8 MB" },
                    { type: "E", name: "Physics 30-Q bank pick", bankRef: "bank-phy-30" },
                ]),
            ],
        },
        {
            id: "srcseed8maths",
            className: "8",
            subject: "Mathematics",
            board: "CBSE",
            chapters: [
                { name: "Rational Numbers", subChapters: ["Properties", "Operations"] },
                { name: "Linear Equations", subChapters: ["One variable", "Word problems"] },
            ],
            resources: [],
        },
        {
            id: "srcseed8english",
            className: "8",
            subject: "English",
            board: "CBSE",
            chapters: [
                { name: "Grammar", subChapters: ["Tenses", "Voice"] },
                { name: "Comprehension", subChapters: ["Passages", "Poems"] },
            ],
            resources: [],
        },
        {
            id: "srcseed7science",
            className: "7",
            subject: "Science",
            board: "CBSE",
            chapters: [
                { name: "Nutrition in Plants", subChapters: ["Photosynthesis", "Modes"] },
                { name: "Heat", subChapters: ["Transfer", "Thermometers"] },
            ],
            resources: [],
        },
    ];
}

function load(): SavedSourceDetail[] {
    if (typeof window === "undefined") return [];
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return seedDefaults();
        const parsed = JSON.parse(raw) as SavedSourceDetail[];
        if (!Array.isArray(parsed) || parsed.length === 0) return seedDefaults();
        // backward-compat: entries saved before resources existed
        return parsed.map((e) => ({ ...e, resources: e.resources ?? [] }));
    } catch {
        return seedDefaults();
    }
}

function persist(entries: SavedSourceDetail[]) {
    try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    } catch {
        // storage unavailable — in-memory only
    }
}

// ---- pure selectors (cascading dropdown chains) ----

export function classesOf(entries: SavedSourceDetail[]): string[] {
    return Array.from(new Set(entries.map((e) => e.className))).sort();
}

export function subjectsFor(entries: SavedSourceDetail[], className: string): string[] {
    return Array.from(
        new Set(
            entries
                .filter((e) => e.className === className)
                .map((e) => e.subject),
        ),
    ).sort();
}

export function chaptersFor(
    entries: SavedSourceDetail[],
    className: string,
    subject: string,
): SavedChapter[] {
    return entries
        .filter((e) => e.className === className && e.subject === subject)
        .flatMap((e) => e.chapters);
}

/** All saved resource items (PDF/image/URL/text/bank) for a
 *  Class · Subject · Chapter — so one chapter can hold many
 *  sources and the teacher picks any/all of them. */
export function resourcesFor(
    entries: SavedSourceDetail[],
    className: string,
    subject: string,
    chapter: string,
): SavedResource[] {
    return entries
        .filter((e) => e.className === className && e.subject === subject)
        .flatMap((e) => e.resources ?? [])
        .filter((r) => r.chapter === chapter);
}

export function useSourceMaster() {
    const [entries, setEntries] = useState<SavedSourceDetail[]>(load);

    const saveSource = useCallback((detail: Omit<SavedSourceDetail, "id" | "resources"> & { resources?: SavedResource[] }) => {
        setEntries((prev) => {
            const next: SavedSourceDetail[] = [
                ...prev,
                { ...detail, id: `srcd${Date.now().toString()}`, resources: detail.resources ?? [] },
            ];
            persist(next);
            return next;
        });
    }, []);

    const removeSource = useCallback((id: string) => {
        setEntries((prev) => {
            const next = prev.filter((e) => e.id !== id);
            persist(next);
            return next;
        });
    }, []);

    /** Save one named resource (PDF/image/URL/text/bank) under
     *  Class · Subject · Board · Chapter. Creates the entry/chapter
     *  if missing, appends to `resources` if present. */
    const saveResource = useCallback(
        (where: { className: string; subject: string; board: string; chapter: string },
            res: Omit<SavedResource, "id" | "createdAt" | "chapter">) => {
            setEntries((prev) => {
                const idx = prev.findIndex(
                    (e) => e.className === where.className && e.subject === where.subject,
                );
                const item: SavedResource = {
                    ...res,
                    chapter: where.chapter,
                    id: `res${Date.now().toString()}`,
                    createdAt: new Date().toISOString(),
                };
                let next: SavedSourceDetail[];
                if (idx === -1) {
                    next = [
                        ...prev,
                        {
                            id: `srcd${Date.now().toString()}`,
                            className: where.className,
                            subject: where.subject,
                            board: where.board,
                            chapters: [{ name: where.chapter, subChapters: [] }],
                            resources: [item],
                        },
                    ];
                } else {
                    next = prev.map((e, i) => {
                        if (i !== idx) return e;
                        const hasChapter = e.chapters.some((c) => c.name === where.chapter);
                        return {
                            ...e,
                            chapters: hasChapter
                                ? e.chapters
                                : [...e.chapters, { name: where.chapter, subChapters: [] }],
                            resources: [...(e.resources ?? []), item],
                        };
                    });
                }
                persist(next);
                return next;
            });
        },
        [],
    );

    const removeResource = useCallback((resourceId: string) => {
        setEntries((prev) => {
            const next = prev.map((e) => ({
                ...e,
                resources: (e.resources ?? []).filter((r) => r.id !== resourceId),
            }));
            persist(next);
            return next;
        });
    }, []);

    return { entries, saveSource, removeSource, saveResource, removeResource };
}