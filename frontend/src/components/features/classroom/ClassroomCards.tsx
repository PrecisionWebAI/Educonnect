"use client";

import { Badge } from "@/components/ui";
import Link from "next/link";
import type { ClassGroup } from "@/types";
import ClassCard from "./ClassCard";

// The principal's Classroom grid: a heading per class, three section cards per
// row beneath it. A class appears only when the school actually uses it.

const STAGE_LABELS: Record<string, string> = {
    pre_primary: "Pre-primary",
    primary: "Primary",
    middle: "Middle",
    secondary: "Secondary",
    senior_secondary: "Senior secondary",
};

export default function ClassroomCards({ groups }: { groups: ClassGroup[] }) {
    if (groups.length === 0) {
        return (
            <div className="glass-tile rounded-2xl p-8 text-center">
                <p className="text-muted-foreground text-sm">
                    No classrooms yet — a class appears here as soon as a student is
                    registered in it or a teacher is assigned to it.
                </p>
            </div>
        );
    }

    return (
        <div className="glass-backdrop space-y-8 rounded-3xl p-4 sm:p-6">
            {groups.map((group) => (
                <section key={group.classroomId}>
                    <header className="mb-3 flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-semibold">{group.className}</h2>
                        <Badge tone="violet">
                            {STAGE_LABELS[group.stage] ?? group.stage}
                        </Badge>
                        <span className="text-muted-foreground text-xs">
                            {group.sectionCount}{" "}
                            {group.sectionCount === 1 ? "section" : "sections"} ·{" "}
                            {group.strength}{" "}
                            {group.strength === 1 ? "student" : "students"}
                        </span>
                    </header>
                    {/* One row per class. The sections scroll horizontally, so a
                        class with ten sections neither wraps nor shrinks its cards.
                        A card opens that section's drill-down. */}
                    <div className="flex items-stretch gap-4 overflow-x-auto pb-2">
                        {group.sections.map((card) => (
                            <Link
                                key={card.sectionId}
                                href={`/dashboard/classroom/${card.sectionId}`}
                                className="w-[270px] shrink-0 sm:w-[290px]"
                            >
                                <ClassCard
                                    classLabel={`${group.className}-${card.sectionName}`}
                                    card={card}
                                />
                            </Link>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );
}
