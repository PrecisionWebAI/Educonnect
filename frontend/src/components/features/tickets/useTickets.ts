"use client";
import { useState } from "react";
import { getTickets } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type TicketTab = "My Tickets" | "Raise" | "Inbox" | "Oversight";

export function useTickets() {
    const ticketsQuery = useApiQuery(["tickets"], getTickets);
    const tickets = ticketsQuery.data ?? [];
    const loading = ticketsQuery.isPending;
    const [tab, setTab] = useState<TicketTab>("My Tickets");

    const openCount = tickets.filter((t) => t.status === "Open").length;
    const inProgressCount = tickets.filter((t) => t.status === "In Progress").length;
    const resolvedCount = tickets.filter(
        (t) => t.status === "Resolved" || t.status === "Closed",
    ).length;

    return { tickets, loading, tab, setTab, openCount, inProgressCount, resolvedCount };
}
