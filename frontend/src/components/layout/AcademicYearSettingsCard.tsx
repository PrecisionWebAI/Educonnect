"use client";

import { Card } from "@/components/ui";
import { academicYearRange } from "@/lib/academic-year/view";
import { useAcademicYear } from "@/providers/academic-year-context";

import { AcademicYearSelect } from "./AcademicYearSelect";

/**
 * Settings' view of the same academic-year context as the navbar.
 *
 * It deliberately embeds `AcademicYearSelect` instead of re-implementing
 * open/switch: there is one service, one confirmation and one manager rule.
 */
export default function AcademicYearSettingsCard() {
    const { current, isLoading, canManage } = useAcademicYear();

    return (
        <Card title="Academic year">
            <div className="space-y-3">
                <p className="text-muted-foreground text-sm">
                    The year every admission, course, exam, fee and timetable screen
                    uses. A year runs from 1 April to 31 March.
                </p>
                <div className="flex flex-wrap items-center gap-3">
                    <AcademicYearSelect />
                    {isLoading && !current && (
                        <span className="text-muted-foreground text-sm">Loading…</span>
                    )}
                    {current && (
                        <span className="text-muted-foreground text-sm">
                            {academicYearRange(current)}
                        </span>
                    )}
                </div>
                {!canManage && (
                    <p className="text-muted-foreground text-xs">
                        Only a school admin or a role senior to the principal can
                        open or switch the academic year.
                    </p>
                )}
            </div>
        </Card>
    );
}
