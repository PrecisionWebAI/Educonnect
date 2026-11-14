"use client";
import { getReportCards, getDataQuality, getStaffSummaryReport } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export function useReports() {
    const cardsQuery = useApiQuery(["reports", "cards"], getReportCards);
    const qualityQuery = useApiQuery(["reports", "quality"], getDataQuality);
    // The staff aggregates answer a different question from the seeded cards, so they
    // are a separate read: one is "what the school recorded", the other is "what is
    // happening in the register and the season right now".
    const staffQuery = useApiQuery(["reports", "staff-summary"], () => getStaffSummaryReport());
    const cards = cardsQuery.data ?? [];
    const quality = qualityQuery.data ?? [];
    const loading = cardsQuery.isPending || qualityQuery.isPending;

    const criticalCount = quality.filter((q) => q.status === "Critical").length;
    const attentionCount = quality.filter((q) => q.status === "Attention").length;
    const avgScore = quality.length
        ? Math.round(quality.reduce((s, q) => s + q.score, 0) / quality.length)
        : 0;

    return {
        cards,
        quality,
        loading,
        criticalCount,
        attentionCount,
        avgScore,
        staff: staffQuery.data ?? null,
        staffLoading: staffQuery.isPending,
        staffError: staffQuery.error ?? null,
    };
}
