"use client";
import { useState } from "react";
import { getMeetings } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type MeetingTab = "Upcoming" | "Book" | "Pending" | "History";

export function useMeetings() {
    const meetingsQuery = useApiQuery(["meetings"], getMeetings);
    const meetings = meetingsQuery.data ?? [];
    const loading = meetingsQuery.isPending;
    const [tab, setTab] = useState<MeetingTab>("Upcoming");

    const pendingCount = meetings.filter((m) => m.type === "Pending").length;
    const doneCount = meetings.filter((m) => m.type === "Done").length;

    const filtered = meetings.filter((m) => {
        if (tab === "Pending") return m.type === "Pending";
        if (tab === "History") return m.type === "Done";
        if (tab === "Book") return false;
        return m.type === "Scheduled";
    });

    return { meetings, filtered, loading, tab, setTab, pendingCount, doneCount };
}
