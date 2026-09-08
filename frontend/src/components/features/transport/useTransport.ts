"use client";
import { useMemo, useState } from "react";
import { getTransportRoutes, getBuses } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type TransportTab = "Routes & Stops" | "Buses & GPS" | "Fees & Enforcement";

export function useTransport() {
    const routesQuery = useApiQuery(["transport", "routes"], getTransportRoutes);
    const busesQuery = useApiQuery(["transport", "buses"], getBuses);
    const routes = routesQuery.data ?? [];
    const buses = busesQuery.data ?? [];
    const loading = routesQuery.isPending || busesQuery.isPending;

    const totalStudents = useMemo(() => routes.reduce((a, r) => a + r.students, 0), [routes]);
    const activeRoutes = routes.filter((r) => r.status === "Active").length;
    const enRoute = buses.filter((b) => b.status === "En route").length;
    const avgOccupancy = useMemo(() => {
        if (buses.length === 0) return 0;
        const sum = buses.reduce((a, b) => a + (b.occupied / b.capacity) * 100, 0);
        return Math.round(sum / buses.length);
    }, [buses]);

    return {
        routes,
        buses,
        loading,
        totalStudents,
        activeRoutes,
        enRoute,
        avgOccupancy,
    };
}
