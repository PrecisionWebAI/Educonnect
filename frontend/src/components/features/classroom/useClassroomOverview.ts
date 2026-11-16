"use client";

import { useMemo } from "react";
import { getClassroomOverview } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

/** The school-wide class grid (principal and above). */
export function useClassroomOverview() {
    const query = useApiQuery(["classroom", "overview"], getClassroomOverview);
    const groups = useMemo(
        () =>
            (query.data ?? []).map((group) => ({
                ...group,
                stage: group.stage
                    .trim()
                    .toLowerCase()
                    .replace(/[\s-]+/g, "_"),
            })),
        [query.data],
    );

    return {
        groups,
        loading: query.isPending,
        error: query.error,
        hasData: query.data !== undefined,
    };
}
