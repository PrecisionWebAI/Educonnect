"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui";
import {
    isHighestClass,
    nextClassOf,
    higherClasses,
    studentsLabel,
} from "@/lib/students/promotion";
import type { CatalogClass, DepromotePreview } from "@/types";

/**
 * The promotion actions, right-aligned above the table.
 *
 * - **Promote to <next class>** is a split button: the main part promotes the ticked
 *   students to the next class; the arrow ("Next") lets the admin pick any other class,
 *   and picking one first asks "N students will be promoted directly to <class>. Are you
 *   sure?". For the highest class the main part and the menu say **Completed** instead.
 * - **Retain** keeps them in the same class next year.
 * - **De-promote** moves the ticked students one class down - the class they came from -
 *   and asks for the section (A - J) the same way Promote does. It is available only when
 *   a lower class exists and a ticked student is a new admission or a promoted one.
 */
export default function PromoteBar({
    className,
    classes,
    sectionNames,
    selectedCount,
    busy,
    onPromote,
    onComplete,
    onRetain,
    lowerClass,
    canDepromote,
    onDepromote,
    canUndo,
    retainUndo,
    moveUndo,
    onPreviewUndo,
    onUndo,
    blockedReason,
}: {
    /** The class these students are in now ("Class 6"). */
    className: string;
    classes: CatalogClass[];
    /** Every section letter the school can use ("A" - "J"). */
    sectionNames: string[];
    selectedCount: number;
    busy: boolean;
    /** `undefined` means "the next class" / "the child's own section". */
    onPromote: (target?: CatalogClass, section?: string) => Promise<void>;
    onComplete: () => Promise<void>;
    onRetain: () => Promise<void>;
    /** The class right below this one, or `null` when there is none. */
    lowerClass: CatalogClass | null;
    /** A ticked student can be moved down (new admission / promoted). */
    canDepromote: boolean;
    onDepromote: (section: string) => Promise<void>;
    /** A ticked student has a promote / retain / move down that can be taken back. */
    canUndo: boolean;
    /** Every ticked student is retained: the Retain button becomes "Undo retain". */
    retainUndo: boolean;
    /** Every ticked student was moved down: De-promote becomes "Undo de-promote". */
    moveUndo: boolean;
    onPreviewUndo: () => Promise<DepromotePreview>;
    onUndo: () => Promise<void>;
    /** Why Promote and Retain are unavailable (the next session does not exist), or null. */
    blockedReason: string | null;
}) {
    const [menuOpen, setMenuOpen] = useState(false);
    // The menu is two steps: a class first, then its section (A - J).
    const [menuClass, setMenuClass] = useState<CatalogClass | null>(null);
    const [pickedClass, setPickedClass] = useState<{
        klass: CatalogClass;
        section: string;
    } | null>(null);
    const [demoteOpen, setDemoteOpen] = useState(false);
    const [preview, setPreview] = useState<DepromotePreview | null>(null);
    const menu = useRef<HTMLDivElement | null>(null);
    const demoteBox = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        function close(event: MouseEvent) {
            // Each menu closes only on a click outside **itself**: the De-promote menu sits
            // outside the Promote one, and closing it on mousedown would remove its section
            // buttons before their click could land.
            const target = event.target as Node;
            if (menu.current && !menu.current.contains(target)) setMenuOpen(false);
            if (demoteBox.current && !demoteBox.current.contains(target)) setDemoteOpen(false);
        }
        document.addEventListener("mousedown", close);
        return () => document.removeEventListener("mousedown", close);
    }, []);

    const highest = isHighestClass(classes, className);
    const next = nextClassOf(classes, className);
    const none = selectedCount === 0;
    const blocked = blockedReason !== null;
    // Both halves of the split button wear the same colour: grey while nobody is ticked,
    // the primary colour once somebody is.
    const tone =
        none || blocked ? "bg-muted text-muted-foreground hover:bg-muted disabled:opacity-100" : "";

    /** Take the last action back; when data would be deleted, show it and ask first. */
    async function undo() {
        setMenuOpen(false);
        setDemoteOpen(false);
        const found = await onPreviewUndo();
        if (found.attendance + found.fees + found.marks === 0) {
            await onUndo();
            return;
        }
        setPreview(found);
    }

    const demoteReady = !none && (moveUndo || (Boolean(lowerClass) && canDepromote));
    const demoteTone = demoteReady
        ? ""
        : "bg-muted text-muted-foreground hover:bg-muted disabled:opacity-100";

    return (
        <>
            <div className="flex flex-wrap items-center justify-end gap-2">
                <span className="text-muted-foreground mr-auto text-sm">
                    {none
                        ? "Tick students to promote them."
                        : `${studentsLabel(selectedCount)} selected`}
                </span>

                <div className="relative inline-flex" ref={menu}>
                    <Button
                        size="sm"
                        disabled={none || busy || (blocked && !highest) || (!highest && !next)}
                        title={blocked && !highest ? (blockedReason ?? undefined) : undefined}
                        className={`rounded-r-none ${blocked && !highest ? tone : none ? tone : ""}`}
                        onClick={() => (highest ? void onComplete() : void onPromote())}
                    >
                        {highest ? "Completed" : `Promote to ${next?.name ?? "next class"}`}
                    </Button>
                    <Button
                        size="sm"
                        aria-label="Next"
                        disabled={busy || blocked}
                        title={blockedReason ?? "Choose another class"}
                        className={`rounded-l-none border-l border-white/30 px-2 ${tone}`}
                        onClick={() => {
                            setMenuClass(null);
                            setMenuOpen((open) => !open);
                        }}
                    >
                        <ChevronDown className="h-4 w-4" />
                    </Button>
                    {menuOpen && (
                        <div
                            role="menu"
                            className="bg-popover text-popover-foreground absolute top-full right-0 z-30 mt-1 max-h-72 min-w-48 overflow-auto rounded-md border p-1 shadow-md"
                        >
                            {canUndo && !menuClass && (
                                <button
                                    type="button"
                                    role="menuitem"
                                    className="hover:bg-accent mb-1 block w-full rounded border-b px-3 py-1.5 text-left text-sm font-medium"
                                    onClick={() => void undo()}
                                >
                                    Undo promotion
                                </button>
                            )}
                            {none && (
                                <p className="text-muted-foreground px-3 py-1.5 text-xs">
                                    Tick the students first, then pick a class.
                                </p>
                            )}
                            {menuClass ? (
                                <>
                                    <button
                                        type="button"
                                        className="text-muted-foreground hover:bg-accent block w-full rounded px-3 py-1.5 text-left text-xs"
                                        onClick={() => setMenuClass(null)}
                                    >
                                        ← {menuClass.name} · choose a section
                                    </button>
                                    <div className="grid grid-cols-5 gap-1 p-1">
                                        {sectionNames.map((letter) => (
                                            <button
                                                key={letter}
                                                type="button"
                                                role="menuitem"
                                                disabled={none}
                                                aria-label={`${menuClass.name} section ${letter}`}
                                                className="hover:bg-accent rounded border px-2 py-1.5 text-center text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
                                                onClick={() => {
                                                    const klass = menuClass;
                                                    setMenuOpen(false);
                                                    setMenuClass(null);
                                                    if (klass.id === next?.id)
                                                        void onPromote(klass, letter);
                                                    else setPickedClass({ klass, section: letter });
                                                }}
                                            >
                                                {letter}
                                            </button>
                                        ))}
                                    </div>
                                </>
                            ) : highest ? (
                                <button
                                    type="button"
                                    role="menuitem"
                                    disabled={none}
                                    className="hover:bg-accent block w-full rounded px-3 py-1.5 text-left text-sm disabled:cursor-not-allowed disabled:opacity-50"
                                    onClick={() => {
                                        setMenuOpen(false);
                                        void onComplete();
                                    }}
                                >
                                    Completed
                                </button>
                            ) : higherClasses(classes, className).length === 0 ? (
                                <p className="text-muted-foreground px-3 py-1.5 text-sm">
                                    No class above {className}.
                                </p>
                            ) : (
                                higherClasses(classes, className).map((item) => (
                                    <button
                                        key={item.id}
                                        type="button"
                                        role="menuitem"
                                        disabled={none}
                                        className="hover:bg-accent block w-full rounded px-3 py-1.5 text-left text-sm disabled:cursor-not-allowed disabled:opacity-50"
                                        onClick={() => setMenuClass(item)}
                                    >
                                        {item.name}
                                        {item.id === next?.id ? " (next)" : ""}
                                    </button>
                                ))
                            )}
                        </div>
                    )}
                </div>

                <Button
                    size="sm"
                    variant="outline"
                    disabled={none || busy || (blocked && !retainUndo)}
                    title={blocked && !retainUndo ? (blockedReason ?? undefined) : undefined}
                    onClick={() => (retainUndo ? void undo() : void onRetain())}
                >
                    {retainUndo ? "Undo retain" : "Retain"}
                </Button>
                <div className="relative inline-flex" ref={demoteBox}>
                    <Button
                        size="sm"
                        disabled={!demoteReady || busy}
                        title={
                            !lowerClass
                                ? "There is no class below this one."
                                : !canDepromote && !none
                                  ? "Only a new admission or a promoted student can be moved down."
                                  : `Move down to ${lowerClass.name}`
                        }
                        className={demoteTone}
                        onClick={() => {
                            setMenuOpen(false);
                            if (moveUndo) void undo();
                            else setDemoteOpen((open) => !open);
                        }}
                    >
                        {moveUndo ? "Undo de-promote" : "De-promote"}
                    </Button>
                    {demoteOpen && lowerClass && (
                        <div
                            role="menu"
                            className="bg-popover text-popover-foreground absolute top-full right-0 z-30 mt-1 min-w-48 rounded-md border p-1 shadow-md"
                        >
                            <p className="text-muted-foreground px-3 py-1.5 text-xs">
                                Move down to {lowerClass.name} · choose a section
                            </p>
                            <div className="grid grid-cols-5 gap-1 p-1">
                                {sectionNames.map((letter) => (
                                    <button
                                        key={letter}
                                        type="button"
                                        role="menuitem"
                                        aria-label={`${lowerClass.name} section ${letter}`}
                                        className="hover:bg-accent rounded border px-2 py-1.5 text-center text-sm font-medium"
                                        onClick={() => {
                                            setDemoteOpen(false);
                                            void onDepromote(letter);
                                        }}
                                    >
                                        {letter}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <Dialog
                open={pickedClass !== null}
                onOpenChange={(open) => !open && setPickedClass(null)}
            >
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>
                            Promote to {pickedClass?.klass.name}-{pickedClass?.section}?
                        </DialogTitle>
                    </DialogHeader>
                    <p className="text-muted-foreground text-sm">
                        {studentsLabel(selectedCount)} will be promoted directly to{" "}
                        <b>
                            {pickedClass?.klass.name}-{pickedClass?.section}
                        </b>
                        , not the next class. Are you sure?
                    </p>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => setPickedClass(null)}>
                            Cancel
                        </Button>
                        <Button
                            disabled={busy}
                            onClick={async () => {
                                const target = pickedClass;
                                setPickedClass(null);
                                if (target) await onPromote(target.klass, target.section);
                            }}
                        >
                            Yes, promote
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {blockedReason && (
                <p
                    role="status"
                    className="mt-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900"
                >
                    {blockedReason}
                </p>
            )}

            <Dialog open={preview !== null} onOpenChange={(open) => !open && setPreview(null)}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Undo and delete next-year data?</DialogTitle>
                    </DialogHeader>
                    <p className="text-sm">
                        Undoing will permanently delete{" "}
                        <b>
                            {preview?.attendance} attendance entr
                            {preview?.attendance === 1 ? "y" : "ies"}, {preview?.fees} fee record
                            {preview?.fees === 1 ? "" : "s"} and {preview?.marks} mark
                            {preview?.marks === 1 ? "" : "s"}
                        </b>{" "}
                        along with the next-year record. This cannot be undone.
                    </p>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => setPreview(null)}>
                            Cancel
                        </Button>
                        <Button
                            variant="danger"
                            disabled={busy}
                            onClick={async () => {
                                setPreview(null);
                                await onUndo();
                            }}
                        >
                            Delete and undo
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </>
    );
}
