"use client";

import { useCallback, useMemo } from "react";
import { getClassCatalog } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { CatalogClass, CatalogSection, ClassCatalog } from "@/types";

// ============================================================
// useClassCatalog — the school's class vocabulary, straight from the database.
//
// Every class dropdown, section list and stage chip reads this hook, so the UI
// never carries a class list of its own: the rows in `classroom` / `section` are
// the only truth, and a class added there shows up on every screen.
//
// The catalogue changes about once a year, so a cached copy is kept well past the
// default stale time and shared by every screen that asks for it.
// ============================================================

export const CLASS_CATALOG_KEY = ["academics", "catalog"] as const;

/** Classes change once a year; a cached copy is good for five minutes. */
const STALE_TIME_MS = 5 * 60 * 1000;

/** The "do not narrow" entry that the filter dropdowns lead with. */
export const ALL_CLASSES = "All Classes";

export interface ClassCatalogView {
    catalog: ClassCatalog | undefined;
    /** The classes themselves, for callers that need the ids. */
    classes: CatalogClass[];
    /** Class names in school order (Nursery ... Class 12). */
    classNames: string[];
    /** `classNames` prefixed with the "All Classes" filter entry. */
    classOptions: string[];
    /** Every section name in use ("A" ... "J"). */
    sectionNames: string[];
    /** The sections of one class, looked up by name. */
    sectionsOf: (className: string) => CatalogSection[];
    loading: boolean;
}

export function useClassCatalog(): ClassCatalogView {
    const query = useApiQuery(CLASS_CATALOG_KEY, getClassCatalog, {
        staleTime: STALE_TIME_MS,
    });
    const catalog = query.data;

    const classes = useMemo(() => catalog?.classes ?? [], [catalog]);
    const classNames = useMemo(() => classes.map((item) => item.name), [classes]);
    const classOptions = useMemo(
        () => [ALL_CLASSES, ...classNames],
        [classNames],
    );
    const sectionNames = useMemo(
        () => catalog?.sectionNames ?? [],
        [catalog],
    );
    const sectionsOf = useCallback(
        (className: string) =>
            classes.find((item) => item.name === className)?.sections ?? [],
        [classes],
    );

    return {
        catalog,
        classes,
        classNames,
        classOptions,
        sectionNames,
        sectionsOf,
        loading: query.isPending,
    };
}
