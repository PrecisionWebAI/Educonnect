"use client";
import { Spinner, Table, Badge, Card, Button } from "@/components/ui";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetDescription,
} from "@/components/ui/sheet";
import { getPaletteCommands } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { PaletteCommand } from "@/types";
import { useCopilot, type CopilotTab } from "./useCopilot";
import type { CopilotAutomation } from "@/types";
import { useCopilotContext } from "@/providers/copilot-context";

const TABS: CopilotTab[] = ["Ask AI", "Command Palette", "Genius Assistant", "Automations"];

export default function CopilotSheet() {
    const { isOpen, setIsOpen } = useCopilotContext();
    const c = useCopilot();
    const commandsQuery = useApiQuery(["copilot", "commands"], getPaletteCommands);
    const commands = commandsQuery.data ?? [];

    const autoCols = [
        { key: "title", header: "Automation", render: (a: CopilotAutomation) => <b>{a.title}</b> },
        { key: "schedule", header: "Schedule" },
        { key: "lastRun", header: "Last run" },
        {
            key: "active",
            header: "Status",
            render: (a: CopilotAutomation) => (
                <Badge tone={a.active ? "green" : "red"}>{a.active ? "Active" : "Paused"}</Badge>
            ),
        },
    ];

    return (
        <Sheet open={isOpen} onOpenChange={setIsOpen} modal={false}>
            <SheetContent
                side="right"
                hideOverlay
                className="flex w-full flex-col border-l border-white/30 bg-linear-to-br from-(--background)/20 to-(--background)/10 p-0 shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.2)] dark:shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.5)] backdrop-blur-[80px]! sm:max-w-md! dark:border-white/10"
            >
                <div className="flex-1 overflow-y-auto p-6 pb-32">
                    <SheetHeader className="mb-6 text-left">
                        <SheetTitle className="flex items-center gap-2 text-2xl font-bold">
                            <span className="text-primary text-3xl">✨</span>
                            <span className="from-primary to-chart-2 bg-linear-to-r bg-clip-text text-transparent">
                                AI Copilot
                            </span>
                        </SheetTitle>
                        <SheetDescription className="text-muted-foreground text-base">
                            Your intelligent assistant for insights, drafts and automation.
                        </SheetDescription>
                    </SheetHeader>

                    {c.loading ? (
                        <div className="flex justify-center py-10">
                            <Spinner />
                        </div>
                    ) : (
                        <div className="flex h-full flex-col space-y-6">
                            <div className="mb-2 flex gap-4">
                                <div className="flex-1 rounded-2xl border border-(--border-subtle) bg-(--accent-surface)/50 p-4 shadow-sm">
                                    <b className="text-foreground text-2xl font-bold">
                                        {c.automations.length}
                                    </b>
                                    <span className="text-muted-foreground block text-sm">
                                        Automations
                                    </span>
                                </div>
                                <div className="flex-1 rounded-2xl border border-(--border-subtle) bg-(--accent-surface)/50 p-4 shadow-sm">
                                    <b className="text-chart-4 text-2xl font-bold">
                                        {c.activeCount}
                                    </b>
                                    <span className="text-muted-foreground block text-sm">
                                        Running
                                    </span>
                                </div>
                            </div>

                            <div className="no-scrollbar flex overflow-x-auto rounded-xl border border-(--border-subtle) bg-(--accent-surface)/40 p-1 shadow-inner backdrop-blur-md">
                                {TABS.map((t) => (
                                    <button
                                        key={t}
                                        onClick={() => c.setTab(t as CopilotTab)}
                                        className={`min-w-max flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
                                            c.tab === t
                                                ? "bg-card text-foreground border border-(--border-subtle) shadow-sm"
                                                : "text-muted-foreground hover:text-foreground border border-transparent hover:bg-(--accent-surface)/50"
                                        }`}
                                    >
                                        {t}
                                    </button>
                                ))}
                            </div>

                            <div className="flex-1">
                                {c.tab === "Command Palette" && (
                                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                                        <p className="text-muted-foreground mb-4 rounded-lg border border-(--border-subtle) bg-(--accent-surface)/30 p-3 text-sm">
                                            Press{" "}
                                            <kbd className="bg-background rounded-md border px-1.5 py-0.5 shadow-sm">
                                                Ctrl-K
                                            </kbd>{" "}
                                            anywhere in the app to open the palette. Top commands:
                                        </p>
                                        <Table
                                            columns={[
                                                {
                                                    key: "label",
                                                    header: "Command",
                                                    render: (x: PaletteCommand) => (
                                                        <span className="font-medium">
                                                            {x.label}
                                                        </span>
                                                    ),
                                                },
                                                {
                                                    key: "shortcut",
                                                    header: "Shortcut",
                                                    render: (x: PaletteCommand) => (
                                                        <Badge
                                                            tone="accent"
                                                            className="font-mono text-xs shadow-sm"
                                                        >
                                                            {x.shortcut}
                                                        </Badge>
                                                    ),
                                                },
                                                { key: "category", header: "Category" },
                                            ]}
                                            rows={commands}
                                            rowKey={(x) => x.id}
                                            empty="No commands registered."
                                        />
                                    </div>
                                )}

                                {c.tab === "Genius Assistant" && (
                                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                                        <p className="text-muted-foreground mb-4 rounded-lg border border-(--border-subtle) bg-(--accent-surface)/30 p-3 text-sm">
                                            Contextual suggestions based on what you were last
                                            doing.
                                        </p>
                                        <div className="grid grid-cols-1 gap-3">
                                            {c.suggestions.map((s) => (
                                                <div
                                                    key={s.id}
                                                    onClick={() => {
                                                        c.setTab("Ask AI");
                                                        c.setPrompt(s.prompt);
                                                    }}
                                                    className="group cursor-pointer"
                                                >
                                                    <Card className="hover:bg-accent hover:border-primary rounded-xl border-(--border-subtle) bg-(--background)/50 p-4 shadow-sm backdrop-blur-sm transition-all group-hover:shadow-md">
                                                        <Badge tone="teal" className="shadow-sm">
                                                            {s.tag}
                                                        </Badge>
                                                        <p className="text-foreground mt-3 text-sm font-medium">
                                                            {s.prompt}
                                                        </p>
                                                    </Card>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {c.tab === "Ask AI" && (
                                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                                        <h3 className="text-muted-foreground mb-3 text-sm font-semibold tracking-wider uppercase">
                                            Suggested prompts
                                        </h3>
                                        <div className="grid grid-cols-1 gap-3">
                                            {c.suggestions.map((s) => (
                                                <div
                                                    key={s.id}
                                                    onClick={() => c.setPrompt(s.prompt)}
                                                    className="group cursor-pointer"
                                                >
                                                    <Card className="hover:bg-accent hover:border-primary rounded-xl border-(--border-subtle) bg-(--background)/50 p-4 shadow-sm backdrop-blur-sm transition-all group-hover:shadow-md">
                                                        <Badge tone="violet" className="shadow-sm">
                                                            {s.tag}
                                                        </Badge>
                                                        <p className="text-foreground mt-3 text-sm font-medium">
                                                            {s.prompt}
                                                        </p>
                                                    </Card>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {c.tab === "Automations" && (
                                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                                        <Table
                                            columns={autoCols}
                                            rows={c.automations}
                                            rowKey={(a) => a.id}
                                            empty="No automations yet."
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Fixed Search/Input Bottom Bar */}
                <div className="from-background pointer-events-none absolute right-0 bottom-0 left-0 bg-linear-to-t via-(--background)/90 to-transparent p-6 pt-12">
                    <div className="pointer-events-auto flex max-w-full flex-col gap-2">
                        <div className="group focus-within:border-primary relative flex rounded-3xl border border-(--border-subtle) bg-(--card)/80 p-2 shadow-(--elev-2) backdrop-blur-md transition-colors">
                            <textarea
                                placeholder="Message EduConnect AI..."
                                value={c.prompt}
                                onChange={(e) => {
                                    c.setPrompt(e.target.value);
                                    if (c.tab !== "Ask AI") c.setTab("Ask AI");
                                }}
                                className="text-foreground scrollbar-hide placeholder:text-muted-foreground max-h-37.5 min-h-12 flex-1 resize-none border-none bg-transparent py-2.5 pr-12 pl-4 text-sm outline-none"
                                rows={
                                    c.prompt.split("\n").length > 1
                                        ? Math.min(c.prompt.split("\n").length, 5)
                                        : 1
                                }
                            />
                            <Button
                                variant="primary"
                                className="absolute right-2 bottom-2 flex h-9 w-9 items-center justify-center rounded-full p-0 shadow-sm transition-shadow hover:shadow-md"
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    width="16"
                                    height="16"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <line x1="22" y1="2" x2="11" y2="13"></line>
                                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                                </svg>
                            </Button>
                        </div>
                        <p className="text-muted-foreground text-center text-[11px] opacity-70">
                            AI Copilot can make mistakes. Verify important information.
                        </p>
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}
