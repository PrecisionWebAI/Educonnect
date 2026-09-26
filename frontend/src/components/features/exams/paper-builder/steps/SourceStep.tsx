"use client";

// ============================================================
// SourceStep — Step 2 "Source" (blueprint §1.2). Everything
// chapter/source related, moved OUT of Step 1 "Basic Detail":
//   · the class-library chapter picker (each saved chapter shows its
//     attached material as small oval pills, expandable with a
//     dropdown when a type has more than one item)
//   · the selected-chapters summary
//   · save form (＋ Add chapter opens it): pick an existing chapter
//     from the dropdown or type a new one; every attached item
//     (PDF · image · URL · text · bank) shows as plain oval pills and
//     persists while you switch source types, then is saved to the
//     class library.
// ============================================================

import { useRef, useState } from "react";
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

function Field({
    label,
    children,
}: {
    label: string;
    children: React.ReactNode;
}) {
    return (
        <label className="flex min-w-0 flex-col gap-1">
            <span className="text-xs font-medium text-muted-foreground">{label}</span>
            {children}
        </label>
    );
}

/** Question-bank sets ka source — abhi koi backend endpoint nahi hai,
 *  isliye list **khaali** hai (pehle 3 fake sets hardcoded the).
 *  Jab `/exams/question-bank` aayega, seedha yahan fetch karenge. */
const BANK_SETS: { id: string; label: string }[] = [];

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** One item waiting to be saved under the chapter. */
interface DraftItem {
    id: string;
    type: AddType;
    name: string; // file name / url / notes excerpt / bank label
    fileName?: string;
    fileSize?: string;
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
    const [imageFiles, setImageFiles] = useState<File[]>([]);
    const [url, setUrl] = useState("");
    const [urlStatus, setUrlStatus] = useState("");
    const [pasted, setPasted] = useState("");
    const [bankRef, setBankRef] = useState("");
    const [chapterName, setChapterName] = useState("");
    const [attached, setAttached] = useState<DraftItem[]>([]);
    /** Save card sirf tab khulta hai jab ＋ Add chapter dabaya jaye. */
    const [addOpen, setAddOpen] = useState(false);
    const pdfInputRef = useRef<HTMLInputElement>(null);
    const imgInputRef = useRef<HTMLInputElement>(null);

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

    // ---- staged selection (render-adjust sync, no effect) ----
    // checkbox sirf local state badalte hain; Save par commit ke baad committed
    // snapshot badal jata hai aur staged wapas align ho jata hai.
    const committedItemsNow = committedItemIds();
    const committedKey = `${[...b.chapters].sort().join("|")}|${[...committedItemsNow]
        .sort()
        .join("|")}`;
    const [staged, setStaged] = useState<{ key: string; ch: string[]; items: string[] }>(() => ({
        key: committedKey,
        ch: [...b.chapters],
        items: [...committedItemsNow],
    }));
    if (staged.key !== committedKey) {
        setStaged({ key: committedKey, ch: [...b.chapters], items: [...committedItemsNow] });
    }
    const selChapters = staged.ch;
    const selItems = staged.items;

    // ---- staged toggles (commit sirf Save par) ----
    function toggleChapterStaged(name: string) {
        const on = !selChapters.includes(name);
        const nextCh = on ? [...selChapters, name] : selChapters.filter((c) => c !== name);
        const ids = resourcesFor(master.entries, b.className, b.subject, name).map((r) => r.id);
        const nextItems = on
            ? Array.from(new Set([...selItems, ...ids]))
            : selItems.filter((x) => !ids.includes(x));
        setStaged((prev) => ({ ...prev, ch: nextCh, items: nextItems }));
    }

    function toggleItemStaged(r: SavedResource) {
        const nextItems = selItems.includes(r.id)
            ? selItems.filter((x) => x !== r.id)
            : [...selItems, r.id];
        const nextCh = selChapters.includes(r.chapter)
            ? selChapters
            : [...selChapters, r.chapter];
        setStaged((prev) => ({ ...prev, ch: nextCh, items: nextItems }));
    }

    /** Staged vs committed — koi difference ho to Save active. */
    function committedItemIds(): string[] {
        const ids: string[] = [];
        chapterOptions.forEach((c) => {
            resourcesFor(master.entries, b.className, b.subject, c.name).forEach((r) => {
                if (sourceExists(r)) ids.push(r.id);
            });
        });
        return ids;
    }

    function isDirty(): boolean {
        const sameChapters =
            [...selChapters].sort().join("|") === [...b.chapters].sort().join("|");
        const sameItems =
            [...selItems].sort().join("|") === [...committedItemsNow].sort().join("|");
        return !sameChapters || !sameItems;
    }

    /** Staged selection ko committed state me likho (chapters + per-item sources). */
    function commitSelection(nextChapters: string[]) {
        const preCommitted = new Set(committedItemIds());
        const selSet = new Set(nextChapters);
        // hataye gaye chapters → unke saare sources out
        b.chapters
            .filter((c) => !selSet.has(c))
            .forEach((c) => {
                resourcesFor(master.entries, b.className, b.subject, c).forEach((r) =>
                    removeSourceItems(r),
                );
            });
        // bache chapters → staged items in, pehle-se-committed extras out
        nextChapters.forEach((c) => {
            resourcesFor(master.entries, b.className, b.subject, c).forEach((r) => {
                if (selItems.includes(r.id)) {
                    if (!sourceExists(r)) builder.addSource(sourceFrom(r));
                } else if (preCommitted.has(r.id)) {
                    removeSourceItems(r);
                }
            });
        });
        builder.setBasics({ chapters: nextChapters });
    }

    /** Header Save — form (agar valid) + staged selection dono commit, phir form band. */
    function handleHeaderSave() {
        let next = selChapters;
        if (addOpen && canSave()) {
            const ch = saveToClassLibrary();
            if (ch && !next.includes(ch)) next = [...next, ch];
        }
        if (isDirty()) commitSelection(next);
        setAddOpen(false);
        resetAddForm();
    }

    /** Add form ko khaali karo (Cancel / save ke baad). */
    function resetAddForm() {
        setAttached([]);
        setChapterName("");
        clearCurrentTypeInput();
    }

    /** ＋ Add ke neeche wala Save — attached PDF / image / URL / notes / bank
     *  chapter me save hote hain, chapter (naya ho to naya) is paper ke liye
     *  turant select ho jata hai, aur form khula rehta hai taaki usi chapter
     *  me aur material add kiya ja sake. */
    function handleSaveAttached() {
        const ch = saveToClassLibrary();
        if (!ch) return;
        setAttached([]); // pills clear — material save ho gaya
        clearCurrentTypeInput();
        setChapterName(ch); // usi chapter me aage material add kar sakte hain
    }

    /** Save button ka status hint — kya save hoga. */
    function attachStatus(): string {
        if (attached.length === 0) {
            return "Attach at least one item (PDF · image · URL · notes · bank) to save it under a chapter.";
        }
        const ch = chapterName.trim();
        if (!ch) return "Type or pick a chapter name above, then Save.";
        const exists = chapterOptions.some((c) => c.name === ch);
        const n = `${attached.length} item${attached.length === 1 ? "" : "s"}`;
        return `${n} → ${exists ? "added to" : "new chapter"} "${ch}"`;
    }
    // ---- add-chapter draft: attached item pills ----
    function canAdd(): boolean {
        if (picked === "A") return pdfFile !== null;
        if (picked === "B") return imageFiles.length > 0;
        if (picked === "C") return url.trim().length > 0;
        if (picked === "D") return pasted.trim().length > 0;
        if (picked === "E") return bankRef.length > 0; // bank set chuna ho
        return false;
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
            const row = BANK_SETS.find((bx) => bx.id === bankRef);
            if (!row) return;
            setAttached((a) => [...a, { id, type: "E", name: row.label, bankRef }]);
        }
    }

    function removeDraft(id: string) {
        setAttached((a) => a.filter((d) => d.id !== id));
    }

    function canSave(): boolean {
        return chapterName.trim().length > 0 && attached.length > 0;
    }

    /** Attached items ko class library + is paper ke sources me save karta hai;
     *  success par chapter ka naam return karta hai (form caller khud reset kare). */
    function saveToClassLibrary(): string | null {
        if (!canSave()) return null;
        const chapter = chapterName.trim();
        const where = {
            className: b.className || "8",
            subject: b.subject || "General",
            board: "CBSE",
            chapter,
        };
        attached.forEach((d) => {
            master.saveResource(where, {
                type: d.type,
                name: d.name,
                fileName: d.fileName,
                fileSize: d.fileSize,
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
        return chapter;
    }


    return (
        <div className="grid gap-4">
            {/* Source step — class-library chapter picker + selected chapters + save-a-chapter form */}
            <div className="grid gap-3 rounded-md border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">Select Chapter</p>
                    <div className="flex items-center gap-2">
                        {addOpen && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                    setAddOpen(false);
                                    resetAddForm();
                                }}
                            >
                                Cancel
                            </Button>
                        )}
                        <Button
                            variant="primary"
                            size="sm"
                            disabled={addOpen ? !canSave() && !isDirty() : !isDirty()}
                            onClick={handleHeaderSave}
                        >
                            Save
                        </Button>
                        {!addOpen && (
                            <Button variant="outline" size="sm" onClick={() => setAddOpen(true)}>
                                ＋ Add chapter
                            </Button>
                        )}
                    </div>
                </div>
                <div className="grid gap-2">
                    {chapterOptions.length > 0 ? (
                        <div className="grid gap-1.5">
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
                                                checked={selChapters.includes(c.name)}
                                                onChange={() => toggleChapterStaged(c.name)}
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
                                                    <label
                                                        key={g.type}
                                                        title={g.items[0].name}
                                                        className="flex cursor-pointer items-center gap-1 rounded-full border px-2 py-0.5 text-xs text-muted-foreground"
                                                    >
                                                        <input
                                                            type="checkbox"
                                                            checked={selItems.includes(g.items[0].id)}
                                                            onChange={() => toggleItemStaged(g.items[0])}
                                                        />
                                                        <span>{TYPE_META[g.type].name}</span>
                                                    </label>
                                                ) : (
                                                    <details key={g.type} className="relative">
                                                        <summary className="cursor-pointer list-none rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                                                            {TYPE_META[g.type].name} (
                                                            {g.items.filter((it) => selItems.includes(it.id)).length}/
                                                            {g.items.length}) ▾
                                                        </summary>
                                                        <div className="absolute z-10 mt-1 grid w-64 gap-0.5 rounded-md border bg-background p-1 shadow-md">
                                                            {g.items.map((r) => (
                                                                <label
                                                                    key={r.id}
                                                                    className="flex cursor-pointer items-center gap-1.5 px-1.5 py-1 text-xs"
                                                                >
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={selItems.includes(r.id)}
                                                                        onChange={() => toggleItemStaged(r)}
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
                        <p className="text-muted-foreground text-sm">No saved chapter</p>
                    )}
                </div>
            </div>

            {/* 2 — Selected chapters with oval pills of their attached material */}
            {b.chapters.length > 0 && (
                <div className="rounded-md border p-3">
                    <p className="text-sm font-medium">Selected chapters</p>
                    <div className="mt-2 grid gap-1.5">
                        {b.chapters.map((c) => {
                            const committedRes = resourcesFor(
                                master.entries,
                                b.className,
                                b.subject,
                                c,
                            ).filter((r) => sourceExists(r));
                            return (
                                <div
                                    key={c}
                                    className="flex flex-wrap items-center gap-2 rounded border p-1.5 text-sm"
                                >
                                    <span className="font-medium">{c}</span>
                                    {committedRes.length === 0 ? (
                                        <span className="text-xs text-muted-foreground">
                                            (no material selected)
                                        </span>
                                    ) : (
                                        groupByType(committedRes).map((g) => (
                                            <span
                                                key={g.type}
                                                title={g.items.map((r) => r.name).join(", ")}
                                            >
                                                <Badge tone="muted">
                                                    {TYPE_META[g.type].name} {g.items.length}
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

            {/* save form: sirf ＋ Add chapter dabane par khulta hai */}
            {addOpen && (
                <div className="rounded-md border p-3">
                <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <Field label="Chapters">
                        <Input
                            list="chapter-options"
                            placeholder="Select existing or type a new chapter"
                            value={chapterName}
                            onChange={(e) => setChapterName(e.target.value)}
                        />
                        <datalist id="chapter-options">
                            {chapterOptions.map((c) => (
                                <option key={c.name} value={c.name} />
                            ))}
                        </datalist>
                    </Field>
                    <Field label="Source type">
                        <Select
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
                    </Field>
                    <Field label="Include topics">
                        <Input
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
                    </Field>
                    <Field label="Exclude topics">
                        <Input
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
                    </Field>
                </div>
                {/* type-specific input + add button */}
                {picked === "A" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
                        <div className="grid gap-1">
                            <span className="text-xs font-medium text-muted-foreground">File</span>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => pdfInputRef.current?.click()}
                                >
                                    Choose PDF
                                </Button>
                                <span className="text-muted-foreground truncate text-xs">
                                    {pdfFile
                                        ? `${pdfFile.name} · ${formatSize(pdfFile.size)}`
                                        : "No file selected"}
                                </span>
                            </div>
                            <input
                                ref={pdfInputRef}
                                type="file"
                                accept=".pdf,application/pdf"
                                onChange={(e) => setPdfFile(e.target.files?.[0] ?? null)}
                                className="hidden"
                            />
                        </div>
                        <Button variant="outline" size="sm" disabled={!canAdd()} onClick={addDraft}>
                            ＋ Add PDF
                        </Button>
                    </div>
                )}
                {picked === "B" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
                        <div className="grid gap-1">
                            <span className="text-xs font-medium text-muted-foreground">Image(s)</span>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => imgInputRef.current?.click()}
                                >
                                    Choose image(s)
                                </Button>
                                <span className="text-muted-foreground truncate text-xs">
                                    {imageFiles.length > 0
                                        ? `${imageFiles.length} image${imageFiles.length > 1 ? "s" : ""} · ${formatSize(imageFiles.reduce((n, f) => n + f.size, 0))}`
                                        : "No image selected"}
                                </span>
                            </div>
                            <input
                                ref={imgInputRef}
                                type="file"
                                accept="image/*"
                                multiple
                                onChange={(e) =>
                                    setImageFiles(Array.from(e.target.files ?? []))
                                }
                                className="hidden"
                            />
                        </div>
                        <Button variant="outline" size="sm" disabled={!canAdd()} onClick={addDraft}>
                            ＋ Add image(s)
                        </Button>
                    </div>
                )}
                {picked === "C" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto_auto] sm:items-end">
                        <Input
                            placeholder="https://…"
                            value={url}
                            aria-label="Website / URL"
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
                            rows={3}
                            placeholder="Paste the chapter / notes text here…"
                            aria-label="Paste text / notes"
                            value={pasted}
                            onChange={(e) => setPasted(e.target.value)}
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
                        {BANK_SETS.length === 0 ? (
                            <p className="text-muted-foreground text-sm">
                                No question bank set available for this class/subject yet.
                            </p>
                        ) : (
                            <Select
                                aria-label="Question bank"
                                value={bankRef}
                                onChange={(e) => setBankRef(e.target.value)}
                            >
                                {BANK_SETS.map((bx) => (
                                    <option key={bx.id} value={bx.id}>
                                        {bx.label}
                                    </option>
                                ))}
                            </Select>
                        )}
                        <Button variant="outline" size="sm" disabled={!canAdd()} onClick={addDraft}>
                            ＋ Add bank pick
                        </Button>
                    </div>
                )}
                {/* attached pills — stay while switching source types; no heading, no empty text */}
                {attached.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
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

                {/* Save — ＋ Add ke neeche: attached material (PDF · image · URL ·
                    notes · bank) chapter me save hota hai aur yeh chapter is
                    paper ke liye turant select ho jata hai (naya ho to bana ke). */}
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t pt-3">
                    <p className="text-muted-foreground text-xs">{attachStatus()}</p>
                    <Button
                        variant="primary"
                        size="sm"
                        disabled={!canSave()}
                        onClick={handleSaveAttached}
                    >
                        Save
                    </Button>
                </div>

                </div>
            )}
        </div>
    );
}



