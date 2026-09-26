"use client";

// ============================================================
// useSourceMaster — saved "sources with details" library
// (blueprint §1.2).
//
// Poori tarah **teacher ke apne data** par chalti hai:
//   · koi seed / demo chapter ya PDF hardcoded nahi
//   · pehla load = khaali library → UI "No saved chapter" dikhata hai
//   · jo bhi teacher save kare, wahi localStorage me persist hota hai
//   · Class → Subject → Chapter cascade isi library se banta hai
//
// Purane dev builds kuch demo entries localStorage me likh dete the
// (`srcseed…` entries aur `seed-…` resources) → `stripSeeded()` unhe
// ek baar saaf kar deta hai, teacher ki asli entries chhod deta hai.
// ============================================================

import { useCallback, useState } from "react";

export interface SavedResource {
    id: string;
    /** A=PDF · B=image · C=URL · D=pasted text · E=bank */
    type: "A" | "B" | "C" | "D" | "E";
    /** teacher-given name, e.g. "Chapter 2 NCERT PDF" */
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
    /** Backend `ExamSource.id` — jab ye item server par save hua (index ke liye).
     *  Isi id se retrieval filter hoti hai aur delete par vectors bhi hattate hain. */
    sourceId?: number;
    /** Saare backend ids (multi-image upload = ek item, kai sources). */
    sourceIds?: number[];
    /** Server ka content sha256 (dedup: same content = wahi source). */
    contentHash?: string;
    /** Ingest status: pending → ingesting → ready | failed ("local" = backend down). */
    ingestStatus?: "pending" | "ingesting" | "ready" | "failed" | "local";
    /** Fail hone ki asli wajah (backend se). */
    ingestError?: string;
    /** Kitne chunks index hue (status "ready" ka proof). */
    chunkCount?: number;
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

/** Demo-data markers jo purane builds ne likhe the. */
const SEED_ENTRY_PREFIX = "srcseed";
const SEED_RESOURCE_PREFIX = "seed-";

/**
 * Ek baar ka cleanup: hardcoded demo entries/resources hataata hai,
 * teacher ki apni saved entries jaise ki waisi rehti hain.
 */
function stripSeeded(entries: SavedSourceDetail[]): SavedSourceDetail[] {
    return entries
        .filter((e) => !String(e.id ?? "").startsWith(SEED_ENTRY_PREFIX))
        .map((e) => ({
            ...e,
            chapters: e.chapters ?? [],
            resources: (e.resources ?? []).filter(
                (r) => !String(r.id ?? "").startsWith(SEED_RESOURCE_PREFIX),
            ),
        }));
}

function load(): SavedSourceDetail[] {
    if (typeof window === "undefined") return [];
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return [];
        const parsed = JSON.parse(raw) as SavedSourceDetail[];
        if (!Array.isArray(parsed)) return [];
        const clean = stripSeeded(parsed);
        // cleanup hua ho to turant persist — dobara seed wapas na aaye
        if (JSON.stringify(clean) !== JSON.stringify(parsed)) persist(clean);
        return clean;
    } catch {
        return [];
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
        new Set(entries.filter((e) => e.className === className).map((e) => e.subject)),
    ).sort();
}

export function chaptersFor(
    entries: SavedSourceDetail[],
    className: string,
    subject: string,
): SavedChapter[] {
    return entries
        .filter((e) => e.className === className && e.subject === subject)
        .flatMap((e) => e.chapters ?? []);
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

    const saveSource = useCallback(
        (
            detail: Omit<SavedSourceDetail, "id" | "resources"> & {
                resources?: SavedResource[];
            },
        ) => {
            setEntries((prev) => {
                const next: SavedSourceDetail[] = [
                    ...prev,
                    {
                        ...detail,
                        id: `srcd${Date.now().toString()}`,
                        resources: detail.resources ?? [],
                    },
                ];
                persist(next);
                return next;
            });
        },
        [],
    );

    const removeSource = useCallback((id: string) => {
        setEntries((prev) => {
            const next = prev.filter((e) => e.id !== id);
            persist(next);
            return next;
        });
    }, []);

    /** Save one named resource (PDF/image/URL/text/bank) under
     *  Class · Subject · Board · Chapter. Creates the entry/chapter
     *  if missing, appends to `resources` if present.
     *
     *  ⭐ Return: bana hua item (id ke saath). Iski zaroorat isliye hai ki caller
     *  backend se aane wali `sourceId` / ingest status **usi item par** likh sake
     *  (`updateResource`) — warna UI ko kabhi pata nahi chalta ki index hua ya nahi.
     */
    const saveResource = useCallback(
        (
            where: { className: string; subject: string; board: string; chapter: string },
            res: Omit<SavedResource, "id" | "createdAt" | "chapter">,
        ): SavedResource => {
            const item: SavedResource = {
                ...res,
                chapter: where.chapter,
                // Random suffix: same millisecond mein 2 items (PDF + image) save
                // hone par id clash na ho.
                id: `res${Date.now().toString()}-${Math.random().toString(36).slice(2, 7)}`,
                createdAt: new Date().toISOString(),
            };
            setEntries((prev) => {
                const idx = prev.findIndex(
                    (e) => e.className === where.className && e.subject === where.subject,
                );
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
            return item;
        },
        [],
    );

    /** Ek resource ke fields patch karo (backend `sourceId` / ingest status write-back). */
    const updateResource = useCallback(
        (resourceId: string, patch: Partial<SavedResource>) => {
            setEntries((prev) => {
                const next = prev.map((e) => ({
                    ...e,
                    resources: (e.resources ?? []).map((r) =>
                        r.id === resourceId ? { ...r, ...patch } : r,
                    ),
                }));
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

    return { entries, saveSource, removeSource, saveResource, updateResource, removeResource };
}