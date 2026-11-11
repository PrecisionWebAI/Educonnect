"use client";

import { getClassroomOverview } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

/** The school-wide class grid (principal and above). */
export function useClassroomOverview() {
    const query = useApiQuery(["classroom", "overview"], getClassroomOverview);
    return {
        groups: query.data ?? [],
        loading: query.isPending,
    };
}
