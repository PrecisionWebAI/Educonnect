"use client";
import { useState } from "react";
import { getAutomations, getCopilotSuggestions } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type CopilotTab = "Ask AI" | "Command Palette" | "Genius Assistant" | "Automations";

export function useCopilot() {
    const automationsQuery = useApiQuery(["copilot", "automations"], getAutomations);
    const suggestionsQuery = useApiQuery(["copilot", "suggestions"], getCopilotSuggestions);
    const automations = automationsQuery.data ?? [];
    const suggestions = suggestionsQuery.data ?? [];
    const loading = automationsQuery.isPending || suggestionsQuery.isPending;
    const [tab, setTab] = useState<CopilotTab>("Ask AI");
    const [prompt, setPrompt] = useState("");

    const activeCount = automations.filter((a) => a.active).length;

    return { automations, suggestions, loading, tab, setTab, prompt, setPrompt, activeCount };
}
