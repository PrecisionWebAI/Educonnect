"use client";
import { useState } from "react";
import { Badge, Button, Card, Input, Modal, Spinner, Table } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { todayISO } from "@/lib/format";
import { getStaff } from "@/services";
import type { AbsentClass, SubstitutionAbsence, SubstitutionPeriod } from "@/types";
import { useSubstitution } from "./useSubstitution";

/** What the board says about where an absence came from. */
/**
 * What is left to do for one absent teacher, in plain words: "1 period, needs a substitute",
 * "3 periods, 1 still needs a substitute" or "2 periods, all covered".
 */
function coverSummary(total: number, open: number): string {
    const periods = `${total} ${total === 1 ? "period" : "periods"}`;
    if (open === 0) return `${periods}, all covered`;
    if (open === total) {
        return total === 1 ? `${periods}, needs a substitute` : `${periods}, none covered yet`;
    }
    return `${periods}, ${open} still ${open === 1 ? "needs" : "need"} a substitute`;
}

const SOURCE_LABEL: Record<SubstitutionAbsence["source"], string> = {
    leave: "Approved leave",
    register: "Absent on attendance",
    written: "Cover arranged",
};

/**
 * The cover sheet for one day.
 *
 * Three things this screen refuses to do:
 *
 * * **claim cover it does not have.** An open period says "Nobody yet" and offers
 *   `Cover`; a covered one names the substitute and how far it is signed;
 * * **hide why.** The candidate dialog lists the colleagues who *cannot* take the
 *   period with the reason ("On approved Sick leave", "Teaching Class 9-A at 09:00"),
 *   not just the ones who can;
 * * **reason from an empty timetable.** A weekday with no periods says so, instead
 *   of printing "0 open" for a school that has not built its timetable.
 */
export default function SubstitutionTab({
    canAssign,
    canApprove,
}: {
    /** `substitutions.assign` - arranging cover (an HOD: own department only). */
    canAssign: boolean;
    /** `substitutions.approve` - signing it off (the office). */
    canApprove: boolean;
}) {
    const [date, setDate] = useState(todayISO());
    const s = useSubstitution({ date });
    const board = s.board;
    const closed = board !== null && board.isOpen === false;

    // Class attendance: while a class teacher is away, who takes that class's register today?
    // "Same teacher" is whoever already covers one of its periods; "Other" opens the teacher
    // list. Either way the teacher gets access to that one class, that one day, once approved.
    const toast = useToast();
    const [attendanceFor, setAttendanceFor] = useState<AbsentClass | null>(null);
    const [otherOpen, setOtherOpen] = useState(false);
    const [search, setSearch] = useState("");
    const roll = useApiQuery(["staff", "all", "teacher"], () => getStaff({}, "teacher"), {
        enabled: attendanceFor !== null,
    });
    const choices = [...(roll.data ?? [])]
        .filter((person) => person.id !== attendanceFor?.awayTeacherId)
        .filter((person) => person.name.toLowerCase().includes(search.trim().toLowerCase()))
        .sort((a, b) => a.name.localeCompare(b.name));

    function openAttendance(row: AbsentClass) {
        s.setWriteError(null);
        setOtherOpen(false);
        setSearch("");
        setAttendanceFor(row);
    }

    async function giveAttendance(row: AbsentClass, employeeId: string, name: string) {
        const done = await s.giveAttendance(row.classroomId, employeeId);
        if (done) {
            toast.push("success", `${row.classLabel} attendance given to ${name}. Needs approval.`);
            setAttendanceFor(null);
        }
    }

    const columns = [
        { key: "slot", header: "Period" },
        {
            key: "subject",
            header: "Subject",
            render: (row: SubstitutionPeriod) => (
                <div style={{ lineHeight: 1.2 }}>
                    <div>{row.subject || "—"}</div>
                    <div className="text-muted-foreground text-[0.74rem]">
                        {row.classLabel || row.room || ""}
                    </div>
                </div>
            ),
        },
        { key: "absentName", header: "Away" },
        {
            key: "cover",
            header: "Cover",
            render: (row: SubstitutionPeriod) =>
                row.assignment === null ? (
                    <Badge tone="amber">Nobody yet</Badge>
                ) : (
                    <div className="flex items-center gap-2">
                        <span>{row.assignment.substituteName}</span>
                        <Badge tone={row.assignment.status === "Approved" ? "green" : "teal"}>
                            {row.assignment.statusLabel}
                        </Badge>
                    </div>
                ),
        },
        {
            key: "attendance",
            header: "Attendance",
            // Who takes this class's attendance while the teacher is away: the same teacher
            // already covering it, or another one picked from the list. Needs approval.
            render: (row: SubstitutionPeriod) => {
                const room = board?.classes.find((item) => item.classroomId === row.classroomId);
                return room === undefined ? (
                    <span className="text-muted-foreground">—</span>
                ) : (
                    attendanceCell(room)
                );
            },
        },
        {
            key: "actions",
            header: "",
            render: (row: SubstitutionPeriod) => {
                const cover = row.assignment;
                return (
                    <div className="flex gap-2">
                        {canAssign && (
                            <Button
                                variant="ghost"
                                size="sm"
                                disabled={s.busy !== null}
                                onClick={() => s.setPicked(row)}
                            >
                                {cover === null ? "Cover" : "Change"}
                            </Button>
                        )}
                        {canApprove && cover !== null && cover.status === "Assigned" && (
                            <Button
                                variant="ghost"
                                size="sm"
                                disabled={s.busy !== null}
                                onClick={() => void s.approve(cover.id)}
                            >
                                Approve
                            </Button>
                        )}
                        {canAssign && cover !== null && (
                            <Button
                                variant="ghost"
                                size="sm"
                                disabled={s.busy !== null}
                                onClick={() => void s.withdraw(cover.id)}
                            >
                                Withdraw
                            </Button>
                        )}
                    </div>
                );
            },
        },
    ];

    /** The Attendance cell: who has this class's attendance for the day, and its approval. */
    function attendanceCell(room: AbsentClass) {
        const access = room.access;
        if (access === null) {
            return canAssign ? (
                <Button
                    variant="outline"
                    size="sm"
                    disabled={s.busy !== null}
                    onClick={() => openAttendance(room)}
                >
                    Choose ›
                </Button>
            ) : (
                <span className="text-muted-foreground">Nobody yet</span>
            );
        }
        return (
            <div className="flex flex-wrap items-center gap-2">
                <span>{access.delegateName}</span>
                <Badge tone={access.status === "Approved" ? "green" : "teal"}>
                    {access.status === "Approved" ? "Approved" : "Waiting for approval"}
                </Badge>
                {canApprove && access.status === "Assigned" && (
                    <Button
                        variant="ghost"
                        size="sm"
                        disabled={s.busy !== null}
                        onClick={() => void s.approveAttendance(access.id)}
                    >
                        Approve
                    </Button>
                )}
                {canAssign && (
                    <Button
                        variant="ghost"
                        size="sm"
                        disabled={s.busy !== null}
                        onClick={() => openAttendance(room)}
                    >
                        Change
                    </Button>
                )}
            </div>
        );
    }

    // Classes whose away teacher has no period on the list above (a class teacher who teaches
    // nothing today) would otherwise have no row to carry the Attendance button.
    const listedRooms = new Set((board?.periods ?? []).map((item) => item.classroomId));
    const unlistedClasses = (board?.classes ?? []).filter(
        (item) => !listedRooms.has(item.classroomId),
    );
    const classColumns = [
        {
            key: "classLabel",
            header: "Class",
            render: (row: AbsentClass) => <b>{row.classLabel}</b>,
        },
        { key: "awayTeacherName", header: "Class teacher (away)" },
        {
            key: "attendance",
            header: "Attendance",
            render: (row: AbsentClass) => attendanceCell(row),
        },
    ];

    return (
        <div>
            <div className="toolbar">
                <Input
                    type="date"
                    aria-label="Day"
                    value={date}
                    onChange={(event) => setDate(event.target.value || todayISO())}
                />
                {board !== null && !closed && (
                    <Badge tone={board.open === 0 ? "green" : "amber"}>
                        {board.covered} of {board.total} covered
                    </Badge>
                )}
                {s.refreshing && <span className="text-muted-foreground text-xs">Updating…</span>}
            </div>

            {s.loading && <Spinner size="md" />}

            {!s.loading && s.error !== null && (
                <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                    {errorMessage(s.error, "The cover sheet could not be loaded.")}
                </p>
            )}

            {s.writeError !== null && (
                <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                    {errorMessage(s.writeError, "That change was not saved.")}
                </p>
            )}

            {!s.loading && closed && board !== null && (
                <Card>
                    <p className="text-muted-foreground text-sm">
                        The school is closed on {board.weekday} {board.onDate} ({board.closedReason}
                        ). There are no lessons, so nothing needs covering.
                    </p>
                </Card>
            )}

            {!s.loading && board !== null && !closed && (
                <>
                    {board.absences.length === 0 ? (
                        <Card>
                            <p className="text-muted-foreground text-sm">
                                Nobody is away on {board.weekday} {board.onDate}. Nothing needs
                                covering. Absences come from approved leave, anybody marked Absent
                                on the Attendance tab, and entries added here.
                            </p>
                        </Card>
                    ) : (
                        <div className="grid gap-1" style={{ marginBottom: "0.75rem" }}>
                            {board.absences.map((absence) => (
                                <div
                                    key={absence.employeeId}
                                    className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm"
                                >
                                    <b>{absence.name}</b>
                                    {absence.classTeacherOf.length > 0 && (
                                        <span className="text-muted-foreground">
                                            C.T: {absence.classTeacherOf.join(", ")}
                                        </span>
                                    )}
                                    <Badge tone={absence.source === "register" ? "red" : "teal"}>
                                        {SOURCE_LABEL[absence.source]}
                                    </Badge>
                                    <span className="text-muted-foreground">
                                        {absence.source === "leave" || absence.source === "written"
                                            ? `${absence.reason} · `
                                            : ""}
                                        {absence.totalPeriods === 0
                                            ? "no periods"
                                            : coverSummary(
                                                  absence.totalPeriods,
                                                  absence.openPeriods,
                                              )}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {unlistedClasses.length > 0 && (
                        <Card title="Class attendance">
                            <p className="text-muted-foreground mb-3 text-sm">
                                The class teacher is away and has no period below, but somebody
                                still has to take the class register. Choose who: they get access to{" "}
                                <b>the attendance of this class only</b>, for this day, once the
                                office approves.
                            </p>
                            <Table
                                columns={classColumns}
                                rows={unlistedClasses}
                                rowKey={(row) => row.classroomId}
                                empty="No class needs its attendance handed over."
                            />
                        </Card>
                    )}

                    {board.timetableEmpty ? (
                        <Card>
                            <p className="text-muted-foreground text-sm">
                                There is no timetable for {board.weekday} yet, so there is nothing
                                to cover. This screen reads the timetable rather than keeping a copy
                                of it.
                            </p>
                        </Card>
                    ) : (
                        <Table
                            columns={columns}
                            rows={board.periods}
                            rowKey={(row) => row.periodId}
                            empty="No periods need covering."
                        />
                    )}
                </>
            )}

            <Modal
                open={attendanceFor !== null}
                title={
                    attendanceFor === null
                        ? "Class attendance"
                        : `Who takes ${attendanceFor.classLabel} attendance?`
                }
                onClose={() => setAttendanceFor(null)}
            >
                {attendanceFor !== null && (
                    <>
                        <p className="text-muted-foreground mb-3 text-sm">
                            {attendanceFor.awayTeacherName} is away on {board?.weekday}{" "}
                            {board?.onDate}. The person you choose can open{" "}
                            {attendanceFor.classLabel} and save its attendance for this day only -
                            nothing else in that class, and nothing in their own classes changes.
                        </p>

                        {attendanceFor.suggestedEmployeeId !== null &&
                            attendanceFor.suggestedName !== null && (
                                <Button
                                    disabled={s.busy !== null}
                                    onClick={() =>
                                        void giveAttendance(
                                            attendanceFor,
                                            attendanceFor.suggestedEmployeeId as string,
                                            attendanceFor.suggestedName as string,
                                        )
                                    }
                                >
                                    {`Same teacher: ${attendanceFor.suggestedName}`}
                                </Button>
                            )}
                        {attendanceFor.suggestedEmployeeId !== null && (
                            <p className="text-muted-foreground mt-1 mb-3 text-xs">
                                Already covering a period of {attendanceFor.classLabel} today.
                            </p>
                        )}

                        {attendanceFor.access !== null && (
                            <p className="mb-3 text-sm">
                                Now: <b>{attendanceFor.access.delegateName}</b> (
                                {attendanceFor.access.status === "Approved"
                                    ? "approved"
                                    : "waiting for approval"}
                                ).{" "}
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={s.busy !== null}
                                    onClick={async () => {
                                        const done = await s.withdrawAttendance(
                                            attendanceFor.access?.id as string,
                                        );
                                        if (done) setAttendanceFor(null);
                                    }}
                                >
                                    Withdraw
                                </Button>
                            </p>
                        )}

                        <Button
                            variant="outline"
                            disabled={s.busy !== null}
                            onClick={() => setOtherOpen((open) => !open)}
                        >
                            {otherOpen ? "Hide the list" : "Other teacher…"}
                        </Button>

                        {otherOpen && (
                            <div className="mt-3">
                                <Input
                                    placeholder="Search a teacher…"
                                    value={search}
                                    onChange={(event) => setSearch(event.target.value)}
                                />
                                {roll.isPending && <Spinner size="md" />}
                                <div
                                    className="mt-2 grid gap-1 overflow-y-auto"
                                    style={{ maxHeight: "16rem" }}
                                >
                                    {choices.map((person) => (
                                        <div
                                            key={person.id}
                                            className="flex items-center justify-between gap-3 rounded-md border px-3 py-2"
                                        >
                                            <div style={{ lineHeight: 1.25 }}>
                                                <div className="text-sm">{person.name}</div>
                                                <div className="text-muted-foreground text-xs">
                                                    {person.department}
                                                </div>
                                            </div>
                                            <Button
                                                size="sm"
                                                disabled={s.busy !== null}
                                                onClick={() =>
                                                    void giveAttendance(
                                                        attendanceFor,
                                                        person.id,
                                                        person.name,
                                                    )
                                                }
                                            >
                                                Select
                                            </Button>
                                        </div>
                                    ))}
                                    {!roll.isPending && choices.length === 0 && (
                                        <p className="text-muted-foreground text-sm">
                                            No teacher matches.
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}

                        {s.writeError !== null && (
                            <p className="mt-3 text-sm" style={{ color: "var(--danger, #b42318)" }}>
                                {errorMessage(s.writeError, "That was not saved.")}
                            </p>
                        )}
                    </>
                )}
                <div className="mt-4 flex justify-end">
                    <Button variant="ghost" onClick={() => setAttendanceFor(null)}>
                        Close
                    </Button>
                </div>
            </Modal>

            <Modal
                open={s.picked !== null}
                title={
                    s.candidates === null
                        ? "Find a substitute"
                        : `${s.candidates.subject || "Period"} · ${
                              s.candidates.classLabel
                          } · ${s.candidates.slot}`
                }
                onClose={() => s.setPicked(null)}
            >
                {s.candidatesLoading && <Spinner size="md" />}

                {!s.candidatesLoading && s.candidates !== null && (
                    <>
                        {s.candidates.assignment !== null && (
                            <p className="text-sm">
                                This period is already covered by{" "}
                                <b>{s.candidates.assignment.substituteName}</b>. Withdraw that cover
                                first to choose somebody else.
                            </p>
                        )}

                        {s.candidates.assignment === null &&
                            s.candidates.candidates.length === 0 && (
                                <p className="text-sm">
                                    Nobody is free to cover {s.candidates.subject || "this period"}{" "}
                                    at that hour. Widen the search - or cover it yourself.
                                </p>
                            )}

                        {s.candidates.candidates.length > 0 && (
                            <div className="grid gap-2" style={{ marginTop: "0.25rem" }}>
                                {s.candidates.candidates.map((candidate) => (
                                    <div
                                        key={candidate.employeeId}
                                        className="flex items-center justify-between gap-3 rounded-md border p-2"
                                    >
                                        <div style={{ lineHeight: 1.25 }}>
                                            <div className="text-sm">{candidate.name}</div>
                                            {/* The reason, not a bare score: the office can
                                                argue with a sentence, not a number. */}
                                            <div className="text-muted-foreground text-xs">
                                                {candidate.reason}
                                            </div>
                                        </div>
                                        <Button
                                            size="sm"
                                            disabled={s.busy !== null}
                                            onClick={() => {
                                                if (s.picked !== null) {
                                                    void s.assign(s.picked, candidate.employeeId);
                                                }
                                            }}
                                        >
                                            Assign
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        )}

                        {s.candidates.blocked.length > 0 && (
                            <>
                                <p
                                    className="text-muted-foreground mt-3 text-xs"
                                    style={{ marginBottom: "0.25rem" }}
                                >
                                    Teaches the subject but cannot take this period:
                                </p>
                                <div className="grid gap-1">
                                    {s.candidates.blocked.map((row) => (
                                        <div key={row.employeeId} className="text-xs">
                                            <b>{row.name}</b> - {row.reason}
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}
                    </>
                )}

                <div className="mt-4 flex justify-end">
                    <Button variant="ghost" onClick={() => s.setPicked(null)}>
                        Close
                    </Button>
                </div>
            </Modal>
        </div>
    );
}
