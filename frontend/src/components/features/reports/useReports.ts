"use client";
import { useState } from "react";
import { getReportCards, getDataQuality } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export function useReports() {
    const cardsQuery = useApiQuery(["reports", "cards"], getReportCards);
    const qualityQuery = useApiQuery(["reports", "quality"], getDataQuality);
    const cards = cardsQuery.data ?? [];
    const quality = qualityQuery.data ?? [];
    const loading = cardsQuery.isPending || qualityQuery.isPending;

    const criticalCount = quality.filter((q) => q.status === "Critical").length;
    const attentionCount = quality.filter((q) => q.status === "Attention").length;
    const avgScore = quality.length
        ? Math.round(quality.reduce((s, q) => s + q.score, 0) / quality.length)
        : 0;

    return { cards, quality, loading, criticalCount, attentionCount, avgScore };
}
