"use client";

import { useCallback, useMemo, useState } from "react";
import {
    Badge,
    Button,
    Pagination,
    Select,
    Spinner,
    Table,
    type BadgeTone,
    type Column,
} from "@/components/ui";
import {
    filterOptions,
    loadBandOf,
    loadShare,
    matchesFilter,
    sortTeachers,
    uniqueSubjects,
    utilisationShares,
    weekCapacity,
    type SortDirection,
    type TeacherFilterField,
    type TeacherSortKey,
} from "@/lib/course/view";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { getBellSchedule, getCourseTeachers, getWeekOff } from "@/services";
import type { CourseTeacherRow } from "@/types";

import TeacherCourseDetail from "./TeacherCourseDetail";
import TeacherTimetable from "./TeacherTimetable";

/** The filter's first dropdown: which column to look in, and what its second dropdown asks. */
const FILTER_FIELDS: { value: TeacherFilterField; label: string; placeholder: string }[] = [
    { value: "teacher", label: "Teacher", placeholder: "Select teacher" },
    { value: "department", label: "Department", placeholder: "Select department" },
    { value: "classCov", label: "Class COV", placeholder: "Select class" },
    { value: "subjectCov", label: "Subject COV", placeholder: "Select subject" },
];

/** What the Sort by dropdown orders on - the table's own number columns. */
const SORT_KEYS: { value: TeacherSortKey; label: string }[] = [
    { value: "chapters", label: "AVG Chapters/MON" },
    { value: "periods", label: "Periods/wk" },
    { value: "load", label: "Load/wk" },
    { value: "classes", label: "Classes (AY)" },
    { value: "substitution", label: "Substitution (AY)" },
    { value: "utilisation", label: "Utilisation" },
];

/** Classes shown in full in the Class coverage cell; more than this scrolls. */
const CLASS_ROWS_VISIBLE = 6;

/** The Load badge's colour: grey when light, green when steady, red when over the line. */
const LOAD_TONE: Record<CourseTeacherRow["loadBand"], BadgeTone> = {
    Overloaded: "red",
    Steady: "green",
    Light: "muted",
    Unassigned: "amber",
};

/**
 * People -> Teachers -> Course.
 *
 * The list is the server's aggregate: the classes each teacher covers (sections of one
 * class together) and how many approvals are waiting on a reviewer. Clicking a name opens
 * the same detail the teacher sees on their own "My course", so the office and the teacher
 * read one shape.
 */
export default function CourseTab() {
    const [page, setPage] = useState(1);
    const [pageSize] = useState(10);
    const [selected, setSelected] = useState<string | null>(null);
    const [timetableOf, setTimetableOf] = useState<{ id: string; name: string } | null>(null);
    const [filterField, setFilterField] = useState<TeacherFilterField | "">("");
    const [filterValue, setFilterValue] = useState("");
    const [sortKey, setSortKey] = useState<TeacherSortKey | "">("");
    // High to low first: "who carries the most" is the usual question.
    const [sortDir, setSortDir] = useState<SortDirection>("desc");

    const teachers = useApiQuery(["course", "teachers"], () =>
        getCourseTeachers({ limit: 200 }),
    );
    // The school's day and weekly offs: what a full week is, for the Load/wk column.
    const bell = useApiQuery(["timetable", "bell"], getBellSchedule, { retry: false });
    const weekOff = useApiQuery(["timetable", "week-off"], getWeekOff, { retry: false });
    // A failed week-off read falls back to the school default: only Sunday off.
    const weekCapacityNow = weekCapacity(
        bell.data ?? [],
        weekOff.data ? weekOff.data.days.length : 1,
    );

    const allRows = useMemo(() => teachers.data ?? [], [teachers.data]);

    // The second dropdown lists everything the chosen column holds, A-Z.
    const filterChoices = useMemo(
        () => (filterField ? filterOptions(allRows, filterField) : []),
        [allRows, filterField],
    );

    /** Load/wk as the table prints it: the server's figure, or worked out here. */
    const loadOf = useCallback(
        (row: CourseTeacherRow) =>
            row.loadBand
                ? (row.loadPercent ?? 0)
                : loadShare(row.periodsPerWeek ?? 0, weekCapacityNow),
        [weekCapacityNow],
    );

    // Filter first, then sort, then cut the page - so a page is always full of matches.
    const shown = useMemo(() => {
        const filter = filterField ? { field: filterField, value: filterValue } : null;
        return sortTeachers(
            allRows.filter((row) => matchesFilter(row, filter)),
            sortKey,
            sortDir,
            loadOf,
        );
    }, [allRows, filterField, filterValue, sortKey, sortDir, loadOf]);

    const paginated = useMemo(() => {
        const start = (page - 1) * pageSize;
        return shown.slice(start, start + pageSize);
    }, [shown, page, pageSize]);

    if (timetableOf) {
        return (
            <TeacherTimetable
                employeeId={timetableOf.id}
                name={timetableOf.name}
                onBack={() => setTimetableOf(null)}
            />
        );
    }

    if (selected) {
        return (
            <TeacherCourseDetail
                employeeId={selected}
                onBack={() => setSelected(null)}
            />
        );
    }

    const columns: Column<CourseTeacherRow>[] = [
        {
            key: "name",
            header: "Teacher",
            render: (row) => (
                <div className="flex flex-col">
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-auto justify-start px-0 font-semibold"
                        onClick={() => setSelected(row.employeeId)}
                    >
                        {row.name}
                    </Button>
                    {/* C.T = class teacher of, DEPT = department; the label alone when empty. */}
                    <span className="text-muted-foreground text-xs">
                        {row.classTeacherOf && row.classTeacherOf.length > 0
                            ? `C.T: ${row.classTeacherOf
                                  .map((item) => `${item.className} ${item.sections.join(", ")}`)
                                  .join(" · ")}`
                            : "C.T"}
                    </span>
                    <span className="text-muted-foreground text-xs">
                        {row.department ? `DEPT: ${row.department}` : "DEPT"}
                    </span>
                </div>
            ),
        },
        {
            key: "classes",
            header: "Class COV",
            render: (row) =>
                !row.classes || row.classes.length === 0 ? (
                    <span className="text-muted-foreground">—</span>
                ) : (
                    // Six classes show in full; past that the cell scrolls inside itself.
                    <div
                        className="flex flex-col items-start gap-1 overflow-y-auto pr-1"
                        style={{ maxHeight: `${CLASS_ROWS_VISIBLE * 1.75}rem` }}
                    >
                        {row.classes.map((item) => (
                            // One oval per class: "Nursery A, B, C" together.
                            <Badge key={item.className} tone="muted">
                                {item.className} {item.sections.join(", ")}
                            </Badge>
                        ))}
                    </div>
                ),
        },
        {
            key: "subjects",
            header: "Subject COV",
            render: (row) =>
                uniqueSubjects(row.subjects).length === 0 ? (
                    <span className="text-muted-foreground">—</span>
                ) : (
                    <div className="flex max-h-24 flex-wrap gap-1 overflow-y-auto pr-1">
                        {uniqueSubjects(row.subjects).map((name) => (
                            <Badge key={name} tone="muted">
                                {name}
                            </Badge>
                        ))}
                    </div>
                ),
        },
        {
            key: "chaptersPerMonth",
            header: "AVG Chapters/MON",
            align: "center",
            // Chapters completed per whole month, up to the end of last month: the month
            // still running is left out until it closes.
            // Nothing completed (or no whole month yet) is a plain 0, never a dash.
            render: (row) => {
                const done = row.chaptersCompleted ?? 0;
                const months = row.monthsCounted ?? 0;
                return (
                    <span
                        className="tabular-nums"
                        title={
                            months > 0
                                ? `${done} chapter${done === 1 ? "" : "s"} completed in ${months} month${months === 1 ? "" : "s"}, across every class and section (up to last month)`
                                : "No whole month has passed in this session yet"
                        }
                    >
                        {Number((row.chaptersPerMonth ?? 0).toFixed(1))}
                    </span>
                );
            },
        },
        {
            key: "periods",
            header: "Periods/wk",
            align: "center",
            render: (row) => {
                const count = row.periodsPerWeek ?? 0;
                if (count === 0) return <Badge tone="muted">0</Badge>;
                return (
                    <button
                        type="button"
                        className="cursor-pointer rounded-full"
                        title={`Open ${row.name}'s weekly timetable`}
                        aria-label={`Open ${row.name}'s weekly timetable, ${count} periods`}
                        onClick={() => setTimetableOf({ id: row.employeeId, name: row.name })}
                    >
                        <Badge tone="accent">{count}</Badge>
                    </button>
                );
            },
        },
        {
            key: "load",
            header: "Load/wk",
            align: "center",
            // Periods a week as a share of every period the school's week has, worded as the
            // Light / Steady / Overloaded bands. The server's own figure is
            // used when it sends one; otherwise it is worked out here from the same bell
            // schedule and weekly offs, so the cell is never an empty dash.
            render: (row) => {
                const periods = row.periodsPerWeek ?? 0;
                const fromServer = Boolean(row.loadBand);
                if (!fromServer && (bell.isPending || weekOff.isPending))
                    return <span className="text-muted-foreground">…</span>;
                // The school's day could not be read, so there is nothing to divide by.
                if (!fromServer && bell.isError)
                    return <span className="text-muted-foreground">—</span>;
                const percent = fromServer
                    ? (row.loadPercent ?? 0)
                    : loadShare(periods, weekCapacityNow);
                const band = fromServer
                    ? row.loadBand
                    : loadBandOf(percent, weekCapacityNow);
                // 0 periods out of anything, or nothing set up yet: a plain 0%.
                if (percent === 0) return <Badge tone="muted">0%</Badge>;
                return (
                    <span title={`${periods} periods a week`}>
                        <Badge tone={LOAD_TONE[band] ?? "muted"}>
                            {percent}%
                        </Badge>
                    </span>
                );
            },
        },
        {
            key: "classesYearly",
            header: "Classes (AY)",
            align: "center",
            render: (row) => (
                <span
                    className="tabular-nums"
                    title="Classes taken on open school days, from the start of the session to today (weekly offs and holidays left out; a class a substitute took over counts for the substitute)"
                >
                    {row.classesYearly ?? 0}
                </span>
            ),
        },
        {
            key: "substitutions",
            header: "Substitution / Free (AY)",
            align: "center",
            // Plain text, not a button: it is a count to read, with nothing behind it.
            render: (row) => {
                const done = row.substitutionsYearly ?? 0;
                const free = row.freeYearly ?? 0;
                return (
                    <span
                        className="tabular-nums"
                        title={`${done} substitution${done === 1 ? "" : "s"} on open school days this session, out of ${free} free class${free === 1 ? "" : "es"}`}
                    >
                        {done} / {free}
                    </span>
                );
            },
        },
        {
            key: "utilisation",
            header: "Utilisation",
            // A two-colour bar: own classes, then covers on top.
            render: (row) => {
                const share = utilisationShares(
                    row.classesYearly ?? 0,
                    row.substitutionsYearly ?? 0,
                    row.capacityYearly ?? 0,
                );
                return (
                    <div
                        style={{ display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 120 }}
                        title={`${row.classesYearly ?? 0} own classes + ${row.substitutionsYearly ?? 0} substitutions, out of ${row.capacityYearly ?? 0} lesson slots this session`}
                    >
                        <div
                            className="cls-bar"
                            style={{ flex: 1, height: 8, maxWidth: 110, display: "flex" }}
                        >
                            <div className="bar-fill" style={{ width: `${share.classes}%` }} />
                            <div
                                className="bg-amber-400"
                                style={{ width: `${share.substitutions}%`, height: "100%" }}
                            />
                        </div>
                        <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                            {share.total}%
                        </span>
                    </div>
                );
            },
        },
    ];

    return (
        <div className="space-y-3">
            <div className="toolbar" style={{ flexWrap: "wrap", alignItems: "center", gap: 8 }}>
                {/* Filter: pick the column, then pick from everything that column holds. */}
                <div className="w-40">
                    <Select
                        aria-label="Filter by"
                        value={filterField}
                        onChange={(event) => {
                            setFilterField(event.target.value as TeacherFilterField | "");
                            setFilterValue("");
                            setPage(1);
                        }}
                    >
                        <option value="">Filter by…</option>
                        {FILTER_FIELDS.map((field) => (
                            <option key={field.value} value={field.value}>
                                {field.label}
                            </option>
                        ))}
                    </Select>
                </div>
                <div className="w-48">
                    <Select
                        aria-label="Filter value"
                        value={filterValue}
                        disabled={!filterField}
                        onChange={(event) => {
                            setFilterValue(event.target.value);
                            setPage(1);
                        }}
                    >
                        <option value="">
                            {filterField
                                ? FILTER_FIELDS.find((field) => field.value === filterField)
                                      ?.placeholder
                                : "Choose a filter first"}
                        </option>
                        {filterChoices.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </Select>
                </div>

                {/* Sort: pick what to order by; the arrow flips low-to-high / high-to-low. */}
                <div className="w-44">
                    <Select
                        aria-label="Sort by"
                        value={sortKey}
                        onChange={(event) => {
                            setSortKey(event.target.value as TeacherSortKey | "");
                            setPage(1);
                        }}
                    >
                        <option value="">Sort by…</option>
                        {SORT_KEYS.map((item) => (
                            <option key={item.value} value={item.value}>
                                {item.label}
                            </option>
                        ))}
                    </Select>
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    disabled={!sortKey}
                    onClick={() => setSortDir((dir) => (dir === "asc" ? "desc" : "asc"))}
                    title={sortDir === "asc" ? "Low to high (click for high to low)" : "High to low (click for low to high)"}
                    aria-label={sortDir === "asc" ? "Sorted low to high" : "Sorted high to low"}
                >
                    {sortDir === "asc" ? "↑" : "↓"}
                </Button>
                {(filterField || sortKey) && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                            setFilterField("");
                            setFilterValue("");
                            setSortKey("");
                            setPage(1);
                        }}
                    >
                        Clear
                    </Button>
                )}
            </div>

            {teachers.isPending ? (
                <Spinner />
            ) : teachers.error ? (
                <p className="text-sm text-red-500">
                    {errorMessage(
                        teachers.error,
                        "The teachers' course list could not be loaded.",
                    )}
                </p>
            ) : (
                <Table
                    columns={columns}
                    rows={paginated}
                    rowKey={(row) => row.employeeId}
                    empty={
                        filterField && filterValue
                            ? "No teacher matches this filter."
                            : "No teacher has a course assignment yet."
                    }
                />
            )}

            <Pagination
                currentPage={page}
                totalItems={shown.length}
                pageSize={pageSize}
                onPageChange={setPage}
            />
        </div>
    );
}
