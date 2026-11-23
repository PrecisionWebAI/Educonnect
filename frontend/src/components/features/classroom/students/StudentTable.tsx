"use client";

import type { Student } from "@/types";
import { Badge, Button, Table, Pagination, type Column } from "@/components/ui";

const PROMOTION_LABEL = {
    NEW_ADMISSION: "New admission",
    PROMOTED: "Promoted",
    RETAINED: "Retained",
    COMPLETED: "Completed",
} as const;

const PROMOTION_TONE = {
    NEW_ADMISSION: "muted",
    PROMOTED: "green",
    RETAINED: "amber",
    COMPLETED: "green",
} as const;

function initials(name: string) {
    return name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();
}

export default function StudentTable({
    rows,
    totalItems,
    page,
    pageSize,
    onPageChange,
    onView,
    selection,
    layout = "directory",
    onEdit,
    onToggleStatus,
}: {
    rows: Student[];
    totalItems?: number;
    page?: number;
    pageSize?: number;
    onPageChange?: (page: number) => void;
    onView: (s: Student) => void;
    /**
     * `directory` is the school-wide list (Class, Contact, Edit / Mark as left);
     * `section` is the class-section Students tab (Admission Class, Attendance %,
     * promotion columns) - no row actions, the tab promotes instead.
     */
    layout?: "directory" | "section";
    onEdit?: (s: Student) => void;
    onToggleStatus?: (s: Student) => void;
    /** Present only for people who may promote: draws the checkbox column. */
    selection?: {
        selected: Set<string>;
        onToggle: (student: Student) => void;
        /** Tick / untick every student the filters match (all pages). */
        onToggleAll: () => void;
        allSelected: boolean;
        totalMatching: number;
    };
}) {
    const checkboxColumn: Column<Student>[] = selection
        ? [
              {
                  key: "select",
                  header: (
                      <input
                          type="checkbox"
                          aria-label={`Select all ${selection.totalMatching} students`}
                          title="Select every student in this list"
                          checked={selection.allSelected}
                          onChange={selection.onToggleAll}
                      />
                  ),
                  render: (s) => (
                      <input
                          type="checkbox"
                          aria-label={`Select ${s.name}`}
                          checked={selection.selected.has(s.id)}
                          onChange={() => selection.onToggle(s)}
                      />
                  ),
              },
          ]
        : [];

    const columns: Column<Student>[] = [
        ...checkboxColumn,
        {
            key: "name",
            header: "Name",
            render: (s) => (
                <button
                    type="button"
                    className="group flex w-full cursor-pointer items-center gap-3 rounded-xl p-2 text-left transition-colors hover:bg-(--accent-surface)/50"
                    title="View profile"
                    onClick={() => onView(s)}
                >
                    <div className="bg-primary/20 text-primary flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-bold shadow-sm transition-all group-hover:shadow-[0_0_10px_rgba(var(--primary),0.3)]">
                        {initials(s.name)}
                    </div>
                    <div className="flex min-w-0 flex-col">
                        <strong className="text-foreground truncate text-sm">{s.name}</strong>
                        {layout === "section" ? (
                            // The tab tells what happened to the child next year, right
                            // under the name ("Promoted to Class 7"); nothing while Pending.
                            s.nextYearOutcome || s.movedFrom ? (
                                <span className="text-muted-foreground truncate text-xs">
                                    {s.nextYearOutcome || `Moved down from ${s.movedFrom}`}
                                </span>
                            ) : null
                        ) : (
                            <span className="text-muted-foreground truncate text-xs">
                                {s.admissionNo}
                            </span>
                        )}
                    </div>
                </button>
            ),
        },
        {
            key: "admissionYear",
            header: "Admission Year",
            render: (s) => s.admissionYear || "—",
        },
        layout === "section"
            ? {
                  key: "admissionClass",
                  header: "Admission Class",
                  render: (s) => s.admissionClass || "—",
              }
            : {
                  key: "className",
                  header: "Class",
                  // A student with no placement yet has no class to print.
                  render: (s) => (s.className ? `${s.className}-${s.section}` : "Not placed"),
              },
        { key: "gender", header: "Gender", render: (s) => s.gender || "—" },
        {
            key: "guardian",
            header: "Guardian",
            render: (s) => (
                <span>
                    {s.guardian || "—"}
                    {s.guardianEmail ? (
                        <>
                            <br />
                            <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                                {s.guardianEmail}
                            </span>
                        </>
                    ) : null}
                </span>
            ),
        },
        layout === "section"
            ? { key: "phone", header: "Contact Number", render: (s) => s.phone || "—" }
            : { key: "phone", header: "Contact" },
        ...(layout === "section"
            ? [
                  {
                      key: "attendance",
                      header: "Attendance %",
                      render: (s: Student) =>
                          s.attendancePercent === null || s.attendancePercent === undefined
                              ? "—"
                              : `${s.attendancePercent}%`,
                  } as Column<Student>,
              ]
            : []),
        {
            key: "status",
            header: "Status",
            render: (s) => (
                <Badge tone={s.status === "Active" ? "green" : "muted"}>{s.status}</Badge>
            ),
        },
        ...(layout === "section"
            ? [
                  {
                      key: "promotionStatus",
                      header: "Promotion Status",
                      render: (s: Student) => (
                          <Badge tone={PROMOTION_TONE[s.promotionStatus ?? "NEW_ADMISSION"]}>
                              {PROMOTION_LABEL[s.promotionStatus ?? "NEW_ADMISSION"]}
                          </Badge>
                      ),
                  },
              ]
            : []),
        ...(layout === "directory" && (onEdit || onToggleStatus)
            ? [
                  {
                      key: "actions",
                      header: "",
                      align: "right",
                      render: (s: Student) => (
                          <div className="flex items-center justify-end gap-2">
                              {onEdit && (
                                  <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => onEdit(s)}
                                      className="border-(--border-subtle) bg-(--background)/50 backdrop-blur-sm hover:bg-(--accent-surface)"
                                  >
                                      Edit
                                  </Button>
                              )}
                              {onToggleStatus && (
                                  <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => onToggleStatus(s)}
                                      className="hover:bg-(--accent-surface)"
                                      title={
                                          s.status === "Active"
                                              ? "Take the child off the roll - nothing is deleted"
                                              : "Put the child back on the roll"
                                      }
                                  >
                                      {s.status === "Active" ? "Mark as left" : "Bring back"}
                                  </Button>
                              )}
                          </div>
                      ),
                  } as Column<Student>,
              ]
            : []),
    ];

    return (
        <div className="glass-card overflow-hidden rounded-2xl border border-(--border-subtle) shadow-sm">
            <Table
                columns={columns}
                rows={rows}
                rowKey={(s) => s.id}
                empty="No students match your filters."
            />
            {totalItems !== undefined &&
                page !== undefined &&
                pageSize !== undefined &&
                onPageChange && (
                    <Pagination
                        currentPage={page}
                        totalItems={totalItems}
                        pageSize={pageSize}
                        onPageChange={onPageChange}
                    />
                )}
        </div>
    );
}
