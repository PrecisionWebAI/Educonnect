"use client";

// ============================================================
// CoverageStep — blueprint §1.4 (Step 4: Chapter Coverage Module)
// Modes: Auto · Marks-wise (B) · Percentage-wise (C)
// ============================================================

import type { PaperBuilderApi } from "../usePaperBuilder";
import CoverageTable from "../widgets/CoverageTable";
import CoverageCharts from "../widgets/CoverageCharts";

export default function CoverageStep({
    builder,
    availableChapters,
}: {
    builder: PaperBuilderApi;
    availableChapters: string[];
}) {
    return (
        <div className="space-y-6">
            <CoverageCharts builder={builder} availableChapters={availableChapters} />
            <CoverageTable

            plan={builder.state.coverage}
            totalMarks={builder.state.basics.totalMarks}
            availableChapters={availableChapters}
            onModeChange={builder.setCoverageMode}
            onAddChapter={builder.addCoverageChapter}
            onUpdateChapter={builder.updateCoverageChapter}
            onRemoveChapter={builder.removeCoverageChapter}
            />
        </div>
    );
}