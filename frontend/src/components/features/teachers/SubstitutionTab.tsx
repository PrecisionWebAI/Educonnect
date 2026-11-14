"use client";
import { useState } from "react";
import { Badge, Button, Card, Input, Modal, Spinner, Table } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { todayISO } from "@/lib/format";
import type { SubstitutionPeriod } from "@/types";
import { useSubstitution } from "./useSubstitution";

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

    return (
        <div>
            <div className="toolbar">
                <Input
                    type="date"
                    aria-label="Day"
                    value={date}
                    onChange={(event) => setDate(event.target.value || todayISO())}
                />
                {board !== null && (
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

            {!s.loading && board !== null && (
                <>
                    {board.absences.length === 0 ? (
                        <Card>
                            <p className="text-muted-foreground text-sm">
                                Nobody is away on {board.weekday} {board.onDate}. Nothing needs
                                covering.
                            </p>
                        </Card>
                    ) : (
                        <div className="flex flex-wrap gap-2" style={{ marginBottom: "0.75rem" }}>
                            {board.absences.map((absence) => (
                                <Badge key={absence.employeeId} tone="teal">
                                    {absence.name} · {absence.reason} ·{" "}
                                    {absence.totalPeriods === 0
                                        ? "no periods"
                                        : `${absence.openPeriods} of ${absence.totalPeriods} open`}
                                </Badge>
                            ))}
                        </div>
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
                                    Nobody who teaches {s.candidates.subject || "this subject"} is
                                    free at that hour. Widen the search - or cover it yourself.
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
