"use client";

import { Button, Input, PageHeader, Select, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import RoleGuard from "@/components/auth/RoleGuard";
import { errorMessage } from "@/lib/api/client";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import { inr } from "@/lib/format";
import ClassSummaryTable from "./ClassSummaryTable";
import FeeHeadModal from "./FeeHeadModal";
import FeeStructureTable from "./FeeStructureTable";
import { useFeesStructure } from "./useFeesStructure";
import type { FeeStructureRow } from "@/types";

// Operations ▸ Fees Structure (container).
// Publishes the class-wise fee master consumed by Finance (Fees) and the
// student/parent fee screens.

const TABS = ["Fee Structure", "Class Summary"];

export default function FeesStructurePage() {
    const toast = useToast();
    // The class list comes from the database (`classroom`), so a class added in
    // the school setup shows up here without a code change.
    const catalog = useClassCatalog();
    const f = useFeesStructure(catalog.classNames);

    async function submit() {
        const head = f.draft.head.trim();
        const editing = f.editingId !== null;
        try {
            if (!(await f.saveFeeHead())) {
                toast.push("error", "Fee head and a positive amount are required");
                return;
            }
            toast.push(
                "success",
                editing ? `${head} updated` : `${head} added as a draft fee head`,
            );
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not save the fee head"));
        }
    }

    async function toggle(row: FeeStructureRow) {
        try {
            const next = await f.togglePublished(row);
            toast.push("info", `${row.head} (${row.className}) marked ${next}`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not change the publish state"));
        }
    }

    return (
        <RoleGuard allowedRoles={["SYSTEM_ADMIN", "OWNER", "PRINCIPAL", "ACCOUNTANT"]}>
            <div className="page">
                <PageHeader
                    title="Fees Structure"
                    actions={
                        <Button variant="primary" icon="＋" onClick={f.openCreate}>
                            New Fee Head
                        </Button>
                    }
                />

                {f.loading ? (
                    <Spinner />
                ) : (
                    <>
                        <div className="stat-tiles">
                            <div className="stat-tile">
                                <b>{f.counts.heads}</b>
                                <span>Fee Heads</span>
                            </div>
                            <div className="stat-tile">
                                <b>{f.counts.published}</b>
                                <span>Published</span>
                            </div>
                            <div className="stat-tile">
                                <b>{f.counts.drafts}</b>
                                <span>Drafts</span>
                            </div>
                            <div className="stat-tile">
                                <b>{inr(f.counts.recurringValue)}</b>
                                <span>Recurring Value</span>
                            </div>
                        </div>

                        <Tabs
                            tabs={TABS}
                            active={f.tab}
                            onChange={(t) => f.setTab(t as typeof f.tab)}
                        />

                        {f.tab === "Fee Structure" ? (
                            <>
                                <div className="toolbar">
                                    <div className="toolbar-search">
                                        <Input
                                            placeholder="Search fee head or class…"
                                            value={f.query}
                                            onChange={(e) => f.setQuery(e.target.value)}
                                        />
                                    </div>
                                    <Select
                                        value={f.classFilter}
                                        onChange={(e) => f.setClassFilter(e.target.value)}
                                    >
                                        {catalog.classOptions.map((c) => (
                                            <option key={c} value={c}>
                                                {c}
                                            </option>
                                        ))}
                                    </Select>
                                </div>

                                <FeeStructureTable
                                    rows={f.filtered}
                                    onEdit={f.openEdit}
                                    onToggle={toggle}
                                />
                            </>
                        ) : (
                            <ClassSummaryTable rows={f.classSummary} />
                        )}
                    </>
                )}

                <FeeHeadModal
                    open={f.formOpen}
                    editing={f.editingId !== null}
                    draft={f.draft}
                    classNames={catalog.classNames}
                    onChange={f.setDraft}
                    onClose={() => f.setFormOpen(false)}
                    onSubmit={submit}
                />
            </div>
        </RoleGuard>
    );
}
