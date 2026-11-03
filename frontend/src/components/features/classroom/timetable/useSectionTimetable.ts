"use client";

import { useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    createTimetablePeriod,
    deleteTimetablePeriod,
    getSectionTimetable,
    updateTimetablePeriod,
    type TimetablePeriodInput,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

/**
 * One class-section's week — read and written for real.
 *
 * The page is the class-section you opened, so the week comes from
 * `/timetable/class/{classId}?section_id={sectionId}`: the same endpoint the
 * school-wide grid uses, narrowed to this room. Saving writes to
 * `timetableperiod` (create / move) and clearing deletes the row, so the grid
 * behind the Classroom shows the same week.
 */
export function useSectionTimetable({
    sectionId,
    classroomId,
}: {
    sectionId: string;
    classroomId: string;
}) {
    const queryClient = useQueryClient();
    const query = useApiQuery(
        ["classroom", "section", sectionId, "timetable"],
        () => getSectionTimetable(classroomId, sectionId),
        { enabled: Boolean(sectionId && classroomId) },
    );
    // Memoised so the grid keeps one array identity across renders.
    const periods = useMemo(() => query.data ?? [], [query.data]);

    /** The week changed: refresh this grid, the section page and the school grid. */
    async function refresh() {
        await Promise.all([
            queryClient.invalidateQueries({
                queryKey: ["classroom", "section", sectionId, "timetable"],
            }),
            queryClient.invalidateQueries({ queryKey: ["classroom", "section", sectionId] }),
            queryClient.invalidateQueries({ queryKey: ["timetable"] }),
        ]);
    }

    /** Add a period, or move the one already in that slot. */
    async function save(input: TimetablePeriodInput, periodId?: string) {
        if (periodId) await updateTimetablePeriod(periodId, input);
        else await createTimetablePeriod(input);
        await refresh();
    }

    /** Clear a slot. */
    async function clear(periodId: string) {
        await deleteTimetablePeriod(periodId);
        await refresh();
    }

    return { periods, loading: query.isPending, save, clear };
}
