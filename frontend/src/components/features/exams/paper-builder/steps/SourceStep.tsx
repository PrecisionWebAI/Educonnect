"use client";

// ============================================================
// SourceStep — Step 2 "Source" (blueprint §1.2). Everything
// chapter/source related, moved OUT of Step 1 "Basic Detail":
//   · the class-library chapter picker (each saved chapter shows its
//     attached material as small oval pills, expandable with a
//     dropdown when a type has more than one item)
//   · the selected-chapters summary
//   · "To save a chapter" — one chapter at a time; every attached
//     item (PDF · image · URL · text · bank) is listed under the
//     "Attached items" heading as oval pills and persists while you
//     switch source types, then is saved to the class library.
// ============================================================

import { useState } from "react";
import { Badge, Button, Input, Select, Textarea } from "@/components/ui";
import type { PaperBuilderApi } from "../usePaperBuilder";
import {
    chaptersFor,
    resourcesFor,
    useSourceMaster,
    type SavedResource,
} from "../useSourceMaster";

/** Source types — letters are internal only; the UI shows names. */
type AddType = "A" | "B" | "C" | "D" | "E";

const SOURCE_OPTIONS: { value: AddType; label: string }[] = [
    { value: "A", label: "PDF upload" },
    { value: "B", label: "Image upload" },
    { value: "C", label: "Website / URL" },
    { value: "D", label: "Paste text / notes" },
    { value: "E", label: "Question bank" },
];

const TYPE_META: Record<AddType, { name: string; short: string }> = {
    A: { name: "PDF", short: "PDFs" },
    B: { name: "Image", short: "Images" },
    C: { name: "URL", short: "URLs" },
    D: { name: "Notes", short: "Notes" },
    E: { name: "Bank", short: "Bank picks" },
};

const DEMO_BANK = [
    { id: "bank-phy-30", label: "Physics — 30 mixed questions (Class 8)" },
    { id: "bank-chem-25", label: "Chemistry — 25 mixed questions (Class 8)" },
    { id: "bank-bio-20", label: "Biology — 20 mixed questions (Class 8)" },
];

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** One item waiting to be saved under the chapter ("Attached items"). */
interface DraftItem {
    id: string;
    type: AddType;
    name: string; // file name / url / notes excerpt / bank label
    fileName?: string;
    fileSize?: string;
    pages?: string;
    url?: string;
    textExcerpt?: string;
    bankRef?: string;
}

/** Group a chapter's saved resources by type so pills can show "PDF (2)". */
function groupByType(res: SavedResource[]): { type: AddType; items: SavedResource[] }[] {
    const map = new Map<AddType, SavedResource[]>();
    res.forEach((r) => {
        const t = r.type as AddType;
        const arr = map.get(t) ?? [];
        arr.push(r);
        map.set(t, arr);
    });
    return Array.from(map.entries()).map(([type, items]) => ({ type, items }));
}
export default function SourceStep({ builder }: { builder: PaperBuilderApi }) {
    const b = builder.state.basics;
    const sc = builder.state.scope;
    const master = useSourceMaster();

    // chapters saved in the class library → chapter picker
    const chapterOptions = chaptersFor(master.entries, b.className, b.subject);

    // ---- add-chapter form ----
    const [picked, setPicked] = useState<AddType>("A");
    const [pdfFile, setPdfFile] = useState<File | null>(null);
    const [pdfPages, setPdfPages] = useState("");
    const [imageFiles, setImageFiles] = useState<File[]>([]);
    const [url, setUrl] = useState("");
    const [urlStatus, setUrlStatus] = useState("");
    const [pasted, setPasted] = useState("");
    const [bankRef, setBankRef] = useState(DEMO_BANK[0].id);
    const [chapterName, setChapterName] = useState("");
    const [attached, setAttached] = useState<DraftItem[]>([]);
    const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null);

    // ---- sources ⇄ paper linkage (selecting a chapter brings its
    // material into this paper's source set; deselecting removes it) ----
    const sourceIdFor = (r: SavedResource) => `src-${r.id}`;

    function sourceExists(r: SavedResource): boolean {
        return builder.state.sources.some(
            (s) =>
                s.id === sourceIdFor(r) ||
                (s.label === r.name && s.chapters.includes(r.chapter)),
        );
    }

    function sourceFrom(r: SavedResource) {
        return {
            id: sourceIdFor(r),
            sourceType: r.type,
            label: r.name,
            kind: "knowledge" as const,
            strictness: "Flexible" as const,
            chapters: [r.chapter],
            pages: r.pages,
            fileName: r.fileName,
            fileSize: r.fileSize,
            url: r.url,
            textExcerpt: r.textExcerpt,
            bankRef: r.bankRef,
        };
    }

    function removeSourceItems(r: SavedResource) {
        const sid = sourceIdFor(r);
        builder.state.sources.forEach((s) => {
            if (s.id === sid || (s.label === r.name && s.chapters.includes(r.chapter))) {
                builder.removeSource(s.id);
            }
        });
    }

    function toggleChapter(name: string) {
        const on = !b.chapters.includes(name);
        const res = resourcesFor(master.entries, b.className, b.subject, name);
        builder.setBasics({
            chapters: on ? [...b.chapters, name] : b.chapters.filter((c) => c !== name),
        });
        if (on) {
            res.forEach((r) => {
                if (!sourceExists(r)) builder.addSource(sourceFrom(r));
            });
        } else {
            res.forEach((r) => removeSourceItems(r));
        }
    }

    function toggleAttachment(r: SavedResource) {
        if (!b.chapters.includes(r.chapter)) {
            builder.setBasics({ chapters: [...b.chapters, r.chapter] });
        }
        if (sourceExists(r)) {
            removeSourceItems(r);
        } else {
            builder.addSource(sourceFrom(r));
        }
    }
    // ---- add-chapter draft: items accumulate under "Attached items" ----
    function canAdd(): boolean {
        if (picked === "A") return pdfFile !== null;
        if (picked === "B") return imageFiles.length > 0;
        if (picked === "C") return url.trim().length > 0;
        if (picked === "D") return pasted.trim().length > 0;
        return true; // E — bank pick can always be added
    }

    function clearCurrentTypeInput() {
        setPdfFile(null);
        setImageFiles([]);
        setUrl("");
        setUrlStatus("");
        setPasted("");
    }

    function addDraft() {
        const id = `d-${Date.now().toString()}-${Math.random().toString(36).slice(2, 6)}`;
        if (picked === "A" && pdfFile) {
            setAttached((a) => [
                ...a,
                {
                    id,
                    type: "A",
                    name: pdfFile.name,
                    fileName: pdfFile.name,
                    fileSize: formatSize(pdfFile.size),
                    pages: pdfPages.trim() || undefined,
                },
            ]);
            setPdfFile(null);
        } else if (picked === "B" && imageFiles.length > 0) {
            setAttached((a) => [
                ...a,
                {
                    id,
                    type: "B",
                    name: imageFiles.map((f) => f.name).join(", "),
                    fileName: imageFiles.map((f) => f.name).join(", "),
                    fileSize: formatSize(imageFiles.reduce((n, f) => n + f.size, 0)),
                },
            ]);
            setImageFiles([]);
        } else if (picked === "C" && url.trim()) {
            setAttached((a) => [...a, { id, type: "C", name: url.trim(), url: url.trim() }]);
            setUrl("");
            setUrlStatus("");
        } else if (picked === "D" && pasted.trim()) {
            const text = pasted.trim();
            setAttached((a) => [
                ...a,
                {
                    id,
                    type: "D",
                    name: text.length > 40 ? `${text.slice(0, 40)}…` : text,
                    textExcerpt: text.slice(0, 280),
                },
            ]);
            setPasted("");
        } else if (picked === "E") {
            const row = DEMO_BANK.find((bx) => bx.id === bankRef) ?? DEMO_BANK[0];
            setAttached((a) => [...a, { id, type: "E", name: row.label, bankRef }]);
        }
    }

    function removeDraft(id: string) {
        setAttached((a) => a.filter((d) => d.id !== id));
    }

    function canSave(): boolean {
        return chapterName.trim().length > 0 && attached.length > 0;
    }

    function saveToClassLibrary() {
        if (!canSave()) return;
        const chapter = chapterName.trim();
        const where = {
            className: b.className || "8",
            subject: b.subject || "General",
            board: b.board,
            chapter,
        };
        attached.forEach((d) => {
            master.saveResource(where, {
                type: d.type,
                name: d.name,
                fileName: d.fileName,
                fileSize: d.fileSize,
                pages: d.pages,
                url: d.url,
                textExcerpt: d.textExcerpt,
                bankRef: d.bankRef,
            });
            // the chapter's attachments also become part of this paper's sources
            builder.addSource({
                id: `src-${where.className}-${where.subject}-${chapter}-${d.id}`,
                sourceType: d.type,
                label: d.name,
                kind: "knowledge",
                strictness: "Flexible",
                chapters: [chapter],
                pages: d.pages,
                fileName: d.fileName,
                fileSize: d.fileSize,
                url: d.url,
                textExcerpt: d.textExcerpt,
                bankRef: d.bankRef,
            });
        });
        if (!b.chapters.includes(chapter)) {
            builder.setBasics({ chapters: [...b.chapters, chapter] });
        }
        setSaveMsg({
            ok: true,
            text: `Saved ✓ “${chapter}” · ${attached.length} item${attached.length > 1 ? "s" : ""}`,
        });
        setAttached([]);
        setChapterName("");
    }
    return (
        <div className="grid gap-4">
            {/* Source step — class-library chapter picker + selected chapters + save-a-chapter form */}
            <div className="grid gap-3 rounded-md border p-3">
                <p className="text-sm font-medium">Class library chapters</p>
                <div className="grid gap-2">
                    {chapterOptions.length > 0 ? (
                        <div className="grid gap-1.5">
                            <p className="text-sm text-muted-foreground">
                                Chapters saved for Class {b.className} · {b.subject} — select the
                                ones this paper covers.
                            </p>
                            {chapterOptions.map((c) => {
                                const res = resourcesFor(
                                    master.entries,
                                    b.className,
                                    b.subject,
                                    c.name,
                                );
                                const groups = groupByType(res);
                                return (
                                    <div
                                        key={c.name}
                                        className="flex flex-wrap items-center gap-1.5 rounded border p-1.5 text-sm"
                                    >
                                        <label className="flex cursor-pointer items-center gap-1.5">
                                            <input
                                                type="checkbox"
                                                checked={b.chapters.includes(c.name)}
                                                onChange={() => toggleChapter(c.name)}
                                            />
                                            <span className="font-medium">{c.name}</span>
                                        </label>
                                        {groups.length === 0 ? (
                                            <span className="text-xs text-muted-foreground">
                                                (no material yet)
                                            </span>
                                        ) : (
                                            groups.map((g) =>
                                                g.items.length === 1 ? (
                                                    <span
                                                        key={g.type}
                                                        title={g.items[0].name}
                                                        className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground"
                                                    >
                                                        {TYPE_META[g.type].name}
                                                    </span>
                                                ) : (
                                                    <details key={g.type} className="relative">
                                                        <summary className="cursor-pointer list-none rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                                                            {TYPE_META[g.type].name} ({g.items.length}) ▾
                                                        </summary>
                                                        <div className="absolute z-10 mt-1 grid w-64 gap-0.5 rounded-md border bg-background p-1 shadow-md">
                                                            {g.items.map((r) => (
                                                                <label
                                                                    key={r.id}
                                                                    className="flex cursor-pointer items-center gap-1.5 px-1.5 py-1 text-xs"
                                                                >
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={sourceExists(r)}
                                                                        onChange={() => toggleAttachment(r)}
                                                                    />
                                                                    <span className="truncate">{r.name}</span>
                                                                </label>
                                                            ))}
                                                        </div>
                                                    </details>
                                                ),
                                            )
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <Input
                            label="Chapters (comma separated — nothing saved for this subject yet)"
                            value={b.chapters.join(", ")}
                            onChange={(e) =>
                                builder.setBasics({
                                    chapters: e.target.value
                                        .split(",")
                                        .map((c) => c.trim())
                                        .filter(Boolean),
                                })
                            }
                        />
                    )}
                </div>
            </div>
            {/* 2 — Selected chapters with oval pills of their attached material */}
            {b.chapters.length > 0 && (
                <div className="rounded-md border p-3">
                    <p className="text-sm font-medium">Selected chapters</p>
                    <div className="mt-2 grid gap-1.5">
                        {b.chapters.map((c) => {
                            const attachedRes = resourcesFor(
                                master.entries,
                                b.className,
                                b.subject,
                                c,
                            );
                            return (
                                <div
                                    key={c}
                                    className="flex flex-wrap items-center gap-2 rounded border p-1.5 text-sm"
                                >
                                    <span className="font-medium">{c}</span>
                                    {attachedRes.length === 0 ? (
                                        <span className="text-xs text-muted-foreground">
                                            (no sources yet — add below)
                                        </span>
                                    ) : (
                                        attachedRes.map((r) => (
                                            <span key={r.id} title={r.name}>
                                                <Badge tone="muted">
                                                    {TYPE_META[r.type].name}
                                                </Badge>
                                            </span>
                                        ))
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* 3 — To save a chapter: one chapter, every attached item */}
            <div className="rounded-md border p-3">
                <p className="text-sm font-medium">To save a chapter</p>

                <div className="mt-2 grid gap-2 md:grid-cols-6">
                    <Input
                        label="Chapter name"
                        placeholder="e.g. Force & Pressure"
                        value={chapterName}
                        onChange={(e) => setChapterName(e.target.value)}
                    />
                    <Select
                        label="Source type"
                        value={picked}
                        onChange={(e) => {
                            setPicked(e.target.value as AddType);
                            clearCurrentTypeInput();
                        }}
                    >
                        {SOURCE_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                                {o.label}
                            </option>
                        ))}
                    </Select>
                    <Input
                        label="Pages"
                        placeholder="e.g. 12–28"
                        value={pdfPages}
                        onChange={(e) => setPdfPages(e.target.value)}
                    />
                    <Input
                        label="Include topics"
                        placeholder="comma separated"
                        value={sc.includeTopics.join(", ")}
                        onChange={(e) =>
                            builder.setScope({
                                includeTopics: e.target.value
                                    .split(",")
                                    .map((s) => s.trim())
                                    .filter(Boolean),
                            })
                        }
                    />
                    <Input
                        label="Exclude topics"
                        placeholder="comma separated"
                        value={sc.excludeTopics.join(", ")}
                        onChange={(e) =>
                            builder.setScope({
                                excludeTopics: e.target.value
                                    .split(",")
                                    .map((s) => s.trim())
                                    .filter(Boolean),
                            })
                        }
                    />
                    <Input
                        label="Concept coverage"
                        placeholder="Topic:count"
                        value={sc.conceptCoverage.map((c) => `${c.concept}:${c.count}`).join(", ")}
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
                </div>
                {/* type-specific input + add button (items accumulate in Attached items) */}
                {picked === "A" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
                        <label className="grid gap-1 text-sm">
                            <span className="font-medium">PDF file</span>
                            <input
                                type="file"
                                accept=".pdf,application/pdf"
                                onChange={(e) => setPdfFile(e.target.files?.[0] ?? null)}
                                className="text-sm"
                            />
                            {pdfFile && (
                                <span className="text-xs text-muted-foreground">
                                    {pdfFile.name} · {formatSize(pdfFile.size)}
                                </span>
                            )}
                        </label>
                        <Button variant="outline" size="sm" disabled={!canAdd()} onClick={addDraft}>
                            ＋ Add PDF
                        </Button>
                    </div>
                )}
                {picked === "B" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
                        <label className="grid gap-1 text-sm">
                            <span className="font-medium">Image(s)</span>
                            <input
                                type="file"
                                accept="image/*"
                                multiple
                                onChange={(e) =>
                                    setImageFiles(Array.from(e.target.files ?? []))
                                }
                                className="text-sm"
                            />
                            {imageFiles.length > 0 && (
                                <span className="text-xs text-muted-foreground">
                                    {imageFiles.length} image{imageFiles.length > 1 ? "s" : ""} ·{" "}
                                    {formatSize(imageFiles.reduce((n, f) => n + f.size, 0))}
                                </span>
                            )}
                        </label>
                        <Button variant="outline" size="sm" disabled={!canAdd()} onClick={addDraft}>
                            ＋ Add image(s)
                        </Button>
                    </div>
                )}
                {picked === "C" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto_auto] sm:items-end">
                        <Input
                            label="Website / URL"
                            placeholder="https://…"
                            value={url}
                            onChange={(e) => {
                                setUrl(e.target.value);
                                setUrlStatus("");
                            }}
                        />
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                                const v = url.trim();
                                if (!v) {
                                    setUrlStatus("Enter a URL first.");
                                    return;
                                }
                                try {
                                    const u = new URL(v.startsWith("http") ? v : `https://${v}`);
                                    setUrlStatus(
                                        `Looks reachable (demo check): ${u.hostname} ✓`,
                                    );
                                } catch {
                                    setUrlStatus("That URL looks invalid — check and retry.");
                                }
                            }}
                        >
                            Test
                        </Button>
                        <Button variant="outline" size="sm" disabled={!canAdd()} onClick={addDraft}>
                            ＋ Add URL
                        </Button>
                    </div>
                )}
                {picked === "C" && urlStatus && (
                    <p className="mt-1 text-sm text-muted-foreground">{urlStatus}</p>
                )}
                {picked === "D" && (
                    <div className="mt-2 grid gap-2 sm:items-end">
                        <Textarea
                            label="Paste text / notes"
                            rows={3}
                            placeholder="Paste the chapter / notes text here…"
                            value={pasted}
                            onChange={(e) => setPasted(e.target.value)}
                            hint={
                                pasted.trim()
                                    ? `${pasted.trim().split(/\s+/).length} words · ${pasted.trim().length} characters`
                                    : undefined
                            }
                        />
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={!canAdd()}
                            onClick={addDraft}
                            className="justify-self-end"
                        >
                            ＋ Add text
                        </Button>
                    </div>
                )}
                {picked === "E" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
                        <Select
                            label="Question bank"
                            value={bankRef}
                            onChange={(e) => setBankRef(e.target.value)}
                        >
                            {DEMO_BANK.map((bx) => (
                                <option key={bx.id} value={bx.id}>
                                    {bx.label}
                                </option>
                            ))}
                        </Select>
                        <Button variant="outline" size="sm" disabled={!canAdd()} onClick={addDraft}>
                            ＋ Add bank pick
                        </Button>
                    </div>
                )}
                {/* Attached items — oval pills; stay while switching source types */}
                <div className="mt-3">
                    <p className="text-sm font-medium">Attached items</p>
                    {attached.length === 0 ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                            Nothing attached yet — add a PDF, image, URL, text or bank pick above.
                        </p>
                    ) : (
                        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                            {attached.map((d) => (
                                <span
                                    key={d.id}
                                    title={d.name}
                                    className="flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs"
                                >
                                    <span className="font-medium">{TYPE_META[d.type].name}</span>
                                    <span className="max-w-40 truncate text-muted-foreground">
                                        {d.name}
                                    </span>
                                    <button
                                        type="button"
                                        onClick={() => removeDraft(d.id)}
                                        className="text-muted-foreground hover:text-foreground"
                                        aria-label="Remove item"
                                    >
                                        ✕
                                    </button>
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Button
                        variant="primary"
                        size="sm"
                        disabled={!canSave()}
                        onClick={saveToClassLibrary}
                    >
                        💾 Save to class library
                    </Button>
                    {saveMsg && (
                        <span
                            className={`text-sm ${saveMsg.ok ? "text-emerald-600" : "text-red-500"}`}
                        >
                            {saveMsg.text}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}



