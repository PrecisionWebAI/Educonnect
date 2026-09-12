"use client";

// ============================================================
// ScopeStep — blueprint §1.3 (Step 3: Content Scope)
// ============================================================

import { Input, Textarea } from "@/components/ui";
import type { PaperBuilderApi } from "../usePaperBuilder";

export default function ScopeStep({ builder }: { builder: PaperBuilderApi }) {
    const s = builder.state.scope;
    return (
        <div className="grid gap-3">
            <Input
                label="Pages (e.g. 12–27)"
                value={s.pages ?? ""}
                onChange={(e) => builder.setScope({ pages: e.target.value })}
            />
            <Input
                label="Include topics (comma separated)"
                value={s.includeTopics.join(", ")}
                onChange={(e) =>
                    builder.setScope({
                        includeTopics: e.target.value.split(",").map((c) => c.trim()).filter(Boolean),
                    })
                }
            />
            <Input
                label="Exclude topics (comma separated)"
                value={s.excludeTopics.join(", ")}
                onChange={(e) =>
                    builder.setScope({
                        excludeTopics: e.target.value.split(",").map((c) => c.trim()).filter(Boolean),
                    })
                }
            />
            <Textarea
                label="Concept coverage (e.g. Photosynthesis:2, Respiration:3)"
                rows={2}
                value={s.conceptCoverage.map((c) => `${c.concept}:${c.count}`).join(", ")}
                onChange={(e) =>
                    builder.setScope({
                        conceptCoverage: e.target.value
                            .split(",")
                            .map((pair) => pair.trim().split(":"))
                            .filter((p) => p.length === 2 && p[0])
                            .map((pair) => ({ concept: pair[0], count: Number(pair[1]) })),
                    })
                }
            />
            <p className="text-sm text-muted-foreground">
                Chapter list is library-driven — pick chapters in Step 1 (Basic Details) or add
                them in the Coverage step.
            </p>
        </div>
    );
}