"use client";

// ============================================================
// SourceStep — Step 2 "Source" (blueprint §1.2). Everything
// chapter/source related, moved OUT of Step 1 "Basic Detail":
//   · the class-library chapter picker (each saved chapter shows its
//     attached material as small oval pills, expandable with a
//     dropdown when a type has more than one item). Pill par **hover**
//     karne se ✕ aata hai → woh material chapter/library se hat jata hai.
//   · the selected-chapters summary
//   · save form (＋ Add chapter opens it): pick an existing chapter
//     from the dropdown or type a new one; every attached item
//     (PDF · image · URL · text · bank) shows as plain oval pills and
//     persists while you switch source types. "＋ Add …" aur "Save" ek
//     hi row me rehte hain (neeche alag Save row nahi).
// ============================================================

import { useRef, useState } from "react";
import { Badge, Button, Input, Select, Textarea } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import type { PaperBuilderApi } from "../usePaperBuilder";
import {
    createSourceItem,
    deleteSourceItem,
    getSourceStatus,
    uploadSourceFile,
    type SourceCreateBody,
} from "@/services/exam-builder.service";
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
    // ---- actual file handles (Phase 3.1) ----
    // ⚠️ Ye `File` objects hi asli upload karte hain. Pehle hum sirf naam/size
    // rakhte the, isliye backend par file kabhi pahunchti hi nahi thi aur source
    // sirf browser ke localStorage mein rehta tha (RAG ko kuch nahi milta tha).
    file?: File;
    files?: File[];
}

/** Ingest status → chhota badge (pill par dikhta hai). */
function IngestBadge({ r }: { r: SavedResource }) {
    const status = r.ingestStatus;
    if (!status) return null;
    if (status === "ready") {
        return (
            <span
                title={`Indexed — ${r.chunkCount ?? 0} chunk(s) vector DB mein`}
                className="text-emerald-600"
            >
                indexed
            </span>
        );
    }
    if (status === "failed") {
        return (
            <span title={r.ingestError ?? "Ingest fail hua"} className="text-red-600">
                index failed
            </span>
        );
    }
    if (status === "local") {
        return (
            <span title="Backend reachable nahi — sirf browser me save hua (retrieval me nahi aayega)">
                local only
            </span>
        );
    }
    return (
        <span title="Indexing background me chal rahi hai" className="text-amber-600">
            indexing…
        </span>
    );
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
    const { push } = useToast();

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
            // ---- backend identity (Phase 3.1) ----
            // Ye teen fields hi retrieval ko "sirf ye source padho" banate hain:
            // backend `sourceId` se Qdrant payload filter karta hai, aur
            // `ingestStatus` job summary mein dikhta hai.
            sourceId: r.sourceId,
            contentHash: r.contentHash,
            ingestStatus: r.ingestStatus,
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
        void (async () => {
            let next = selChapters;
            if (addOpen && canSave()) {
                const ch = await saveToClassLibrary();
                if (ch && !next.includes(ch)) next = [...next, ch];
            }
            if (isDirty()) commitSelection(next);
            setAddOpen(false);
            resetAddForm();
        })();
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
        void (async () => {
            const ch = await saveToClassLibrary();
            if (!ch) return;
            setAttached([]); // pills clear — material save ho gaya
            clearCurrentTypeInput();
            setChapterName(ch); // usi chapter me aage material add kar sakte hain
        })();
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
                    // ⚠️ File handle rakhna zaroori hai — Save par isi ko backend
                    // upload karte hain (naam se file dobara nahi mil sakti).
                    file: pdfFile,
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
                    files: imageFiles,
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

    /** Chapter ka ek material **hamesha ke liye** hatao — class library se bhi
     *  aur is paper ke sources se bhi. Select Chapter ke pill par hover karne se
     *  ✕ dikhta hai (checkbox sirf staged selection badalta hai; yeh asli delete).
     *
     *  ⭐ Backend par bhi delete hota hai (`DELETE /exams/sources/{id}`) — jisse
     *  **DB row + Qdrant chunks dono** hatt jaate hain. Yehi guarantee hai ki
     *  delete kiya hua source dobara kabhi retrieve na ho.
     */
    function removeMaterial(r: SavedResource) {
        const ids = r.sourceIds?.length ? r.sourceIds : r.sourceId ? [r.sourceId] : [];
        ids.forEach((sid) => {
            // fire-and-forget: UI turant saaf ho, network apna kaam kare
            void deleteSourceItem(sid).then((res) => {
                if (res.source === "mock") {
                    push(
                        "error",
                        `Backend se source ${sid} delete nahi hua (${res.error ?? "offline"}) — vectors baaki ho sakte hain.`,
                    );
                }
            });
        });
        master.removeResource(r.id);
        removeSourceItems(r);
        setStaged((prev) => ({ ...prev, items: prev.items.filter((id) => id !== r.id) }));
    }

    // ---- backend persistence (Phase 3.1) ----
    // Source → server par save → extract/chunk/embed → vector DB. Yahi step
    // "teacher ka content AI ke paas pahunchta hai" ko asli banata hai; pehle sab
    // kuch sirf localStorage mein tha (backend ko kuch pata hi nahi hota tha).

    /** Ek draft item ko backend par bhejo → wapas `{sourceIds, status, …}`.
     *
     *  PDF/image → **file upload** (asli bytes, multipart). URL/notes/bank → JSON
     *  create (inka content payload mein hi hota hai).
     *  Backend reachable nahi → status `"local"` (item browser mein rehta hai,
     *  par UI saaf batata hai ki retrieval mein nahi aayega).
     */
    async function persistDraft(
        d: DraftItem,
        where: { className: string; subject: string; board: string; chapter: string },
    ): Promise<{
        sourceIds: number[];
        contentHash?: string;
        status: SavedResource["ingestStatus"];
        error?: string;
        chunkCount?: number;
    }> {
        const base = {
            sourceType: d.type,
            title: d.name,
            class_name: where.className,
            subject: where.subject,
            board: where.board,
            chapters: [where.chapter],
            teacherName: "",
        };

        // ---- A / B: file(s) upload ----
        const files = d.files?.length ? d.files : d.file ? [d.file] : [];
        if ((d.type === "A" || d.type === "B") && files.length > 0) {
            const ids: number[] = [];
            let lastStatus: SavedResource["ingestStatus"] = "pending";
            let lastError: string | undefined;
            for (const f of files) {
                const res = await uploadSourceFile(f, base);
                if (!res.data) {
                    lastStatus = "local";
                    lastError = res.error;
                    continue;
                }
                ids.push(res.data.sourceId);
                lastStatus = res.data.deduplicated
                    ? "ready" // pehle se indexed (dedup) — dobara embed nahi hua
                    : (res.data.status as SavedResource["ingestStatus"]);
            }
            return { sourceIds: ids, status: lastStatus, error: lastError };
        }

        // ---- C / D / E: JSON create (URL / notes / bank) ----
        const body: SourceCreateBody = {
            ...base,
            label: d.name,
            kind: "knowledge",
            strictness: "Flexible",
            url: d.url,
            textExcerpt: d.textExcerpt,
            fileName: d.fileName,
            bankRef: d.bankRef,
        };
        const res = await createSourceItem(body);
        if (!res.data) {
            return { sourceIds: [], status: "local", error: res.error };
        }
        return {
            sourceIds: [res.data.id],
            contentHash: res.data.content_hash ?? undefined,
            status: res.data.deduplicated
                ? "ready"
                : (res.data.status as SavedResource["ingestStatus"]),
            chunkCount: res.data.chunk_count,
        };
    }

    /** Indexing background mein chalti hai — status ko thoda poll karke update karo.
     *
     *  Kyun poll? Backend `pending → ingesting → ready` batata hai, aur teacher ko
     *  ye pata hona chahiye ki "content tayyar hai ya nahi" (warna Generate
     *  dabane par retrieval khaali aata hai aur wajah samajh nahi aati). */
    async function refreshIngestStatus(resourceId: string, sourceId: number): Promise<void> {
        const delays = [1500, 3000, 5000, 8000, 12000, 20000];
        for (const wait of delays) {
            await new Promise((resolve) => setTimeout(resolve, wait));
            const res = await getSourceStatus(sourceId);
            if (!res.data) {
                // Backend down/network error — poll band karo, "local" na likho
                // (item shayad theek hi hai, bas abhi status nahi mila).
                return;
            }
            const status = res.data.status as SavedResource["ingestStatus"];
            master.updateResource(resourceId, {
                ingestStatus: status,
                ingestError: res.data.error ?? undefined,
                chunkCount: res.data.chunk_count,
                contentHash: res.data.content_hash ?? undefined,
            });
            if (status === "ready" || status === "failed") return;
        }
    }

    function canSave(): boolean {
        return chapterName.trim().length > 0 && attached.length > 0;
    }

    /** Attached items ko class library + is paper ke sources me save karta hai;
     *  success par chapter ka naam return karta hai (form caller khud reset kare). */
    /** Save attached material → class library **aur backend** (blueprint §1.2.1).
     *
     *  ⭐ Yahi wo jagah hai jo pehle tooti hui thi: hum sirf browser ke
     *  localStorage mein likhte the, isliye backend ko teacher ka content kabhi
     *  milta hi nahi tha (na extract, na chunk, na embedding — retrieval khaali).
     *  Ab har item:
     *    1. backend par save hota hai (file upload ya JSON create) → `sourceId`
     *    2. us source ka text index hota hai (background ingest)
     *    3. status `IngestBadge` par dikhta hai (indexing… → indexed / failed)
     *    4. wahi source is paper ke sources mein jaata hai (`sourceId` ke saath),
     *       jisse retrieval **sirf isi source** par filter kar sake
     */
    async function saveToClassLibrary(): Promise<string | null> {
        if (!canSave()) return null;
        const chapter = chapterName.trim();
        const where = {
            className: b.className || "8",
            subject: b.subject || "General",
            board: "CBSE",
            chapter,
        };

        // Pehle backend (async), phir library — taaki saved row ke saath hi
        // `sourceId` / status likh sakein.
        const persisted = await Promise.all(
            attached.map(async (d) => ({ draft: d, info: await persistDraft(d, where) })),
        );

        persisted.forEach(({ draft: d, info }) => {
            // the chapter's attachments also become part of this paper's sources
            const item = master.saveResource(where, {
                type: d.type,
                name: d.name,
                fileName: d.fileName,
                fileSize: d.fileSize,
                url: d.url,
                textExcerpt: d.textExcerpt,
                bankRef: d.bankRef,
                sourceId: info.sourceIds[0],
                sourceIds: info.sourceIds.length ? info.sourceIds : undefined,
                contentHash: info.contentHash,
                ingestStatus: info.status,
                ingestError: info.error,
                chunkCount: info.chunkCount,
            });

            // Pending/ingesting → background poll (status badge live update).
            const firstId = info.sourceIds[0];
            if (firstId && (info.status === "pending" || info.status === "ingesting")) {
                void refreshIngestStatus(item.id, firstId);
            }

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
                sourceId: info.sourceIds[0],
                sourceIds: info.sourceIds.length ? info.sourceIds : undefined,
                contentHash: info.contentHash,
                ingestStatus: info.status,
            });
        });

        // Teacher ko saaf feedback: kitne index hue, kitne local reh gaye.
        const indexed = persisted.filter((p) => p.info.sourceIds.length > 0).length;
        const localOnly = persisted.length - indexed;
        if (localOnly > 0) {
            push(
                "error",
                `${localOnly} item backend par save nahi ho paya (server reachable nahi) — ` +
                    "wo retrieval mein nahi aayega. Server chalu karke dobara Save karo.",
            );
        } else if (indexed > 0) {
            push("success", `${indexed} source save hua — indexing background mein chal rahi hai`);
        }

        if (!b.chapters.includes(chapter)) {
            builder.setBasics({ chapters: [...b.chapters, chapter] });
        }
        return chapter;
    }


    /** Save — "＋ Add …" ke **saath hi** ek hi row me (neeche alag Save row nahi).
     *  Save attached material ko chapter me likhta hai aur wahi chapter is paper
     *  ke liye select kar deta hai (naya ho to bana ke). */
    const saveButton = (
        <Button
            variant="primary"
            size="sm"
            disabled={!canSave()}
            onClick={handleSaveAttached}
            className="justify-self-end"
        >
            Save
        </Button>
    );

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
                                                    <span
                                                        key={g.type}
                                                        className="group/pill flex items-center gap-0.5 rounded-full border px-2 py-0.5 text-xs text-muted-foreground"
                                                    >
                                                        <label
                                                            title={g.items[0].name}
                                                            className="flex cursor-pointer items-center gap-1"
                                                        >
                                                            <input
                                                                type="checkbox"
                                                                checked={selItems.includes(g.items[0].id)}
                                                                onChange={() => toggleItemStaged(g.items[0])}
                                                            />
                                                            <span>{TYPE_META[g.type].name}</span>
                                                        </label>
                                                        <IngestBadge r={g.items[0]} />
                                                        {/* hover ✕ — is material ko chapter/library se hata do */}
                                                        <button
                                                            type="button"
                                                            onClick={() => removeMaterial(g.items[0])}
                                                            title="Remove this material from the chapter"
                                                            aria-label={`Remove ${g.items[0].name}`}
                                                            className="hover:text-foreground opacity-0 transition-opacity group-hover/pill:opacity-100"
                                                        >
                                                            ✕
                                                        </button>
                                                    </span>
                                                ) : (
                                                    <details key={g.type} className="relative">
                                                        <summary className="cursor-pointer list-none rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                                                            {TYPE_META[g.type].name} (
                                                            {g.items.filter((it) => selItems.includes(it.id)).length}/
                                                            {g.items.length}) ▾
                                                        </summary>
                                                        <div className="absolute z-10 mt-1 grid w-64 gap-0.5 rounded-md border bg-background p-1 shadow-md">
                                                            {g.items.map((r) => (
                                                                <div
                                                                    key={r.id}
                                                                    className="group/row flex items-center gap-1 px-1.5 py-1 text-xs"
                                                                >
                                                                    <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-1.5">
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={selItems.includes(r.id)}
                                                                            onChange={() => toggleItemStaged(r)}
                                                                        />
                                                                        <span className="truncate">{r.name}</span>
                                                                    </label>
                                                                    <IngestBadge r={r} />
                                                                    {/* hover ✕ — sirf is ek material ko hatao */}
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => removeMaterial(r)}
                                                                        title="Remove this material from the chapter"
                                                                        aria-label={`Remove ${r.name}`}
                                                                        className="hover:text-foreground opacity-0 transition-opacity group-hover/row:opacity-100"
                                                                    >
                                                                        ✕
                                                                    </button>
                                                                </div>
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
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto_auto] sm:items-end">
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
                        {saveButton}
                    </div>
                )}
                {picked === "B" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto_auto] sm:items-end">
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
                        {saveButton}
                    </div>
                )}
                {picked === "C" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto_auto_auto] sm:items-end">
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
                        {saveButton}
                    </div>
                )}
                {picked === "C" && urlStatus && (
                    <p className="mt-1 text-sm text-muted-foreground">{urlStatus}</p>
                )}
                {picked === "D" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto_auto] sm:items-end">
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
                        >
                            ＋ Add text
                        </Button>
                        {saveButton}
                    </div>
                )}
                {picked === "E" && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto_auto] sm:items-end">
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
                        {saveButton}
                    </div>
                )}
                {/* attached pills — stay while switching source types; no heading, no empty text */}
                {attached.length > 0 && (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
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

                {/* Save button har source-type row me "＋ Add …" ke saath hai
                    (neeche alag row nahi) — isliye yahan sirf pills rehte hain. */}

                </div>
            )}
        </div>
    );
}



