"use client";
import { useState } from "react";
import {
    Badge,
    Button,
    Card,
    Input,
    Modal,
    Select,
    Spinner,
    Table,
    Textarea,
    type BadgeTone,
} from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { todayISO } from "@/lib/format";
import type {
    AppraisalGoalRow,
    AppraisalRow,
    AppraisalStatus,
    ReviewInput,
    SelfAssessmentInput,
} from "@/types";
import { useAppraisal } from "./useAppraisal";

/** The colour each state wears - one map for the chips and the table. */
const TONE: Record<AppraisalStatus, BadgeTone> = {
    Draft: "muted",
    Submitted: "amber",
    Reviewed: "teal",
    Finalized: "green",
};

/** The only ratings this product holds: 1..5, twice. */
const RATINGS = [1, 2, 3, 4, 5];

/** A goal line as the form holds it. */
type GoalDraft = { title: string; target: string };

function goalDrafts(goals: AppraisalGoalRow[]): GoalDraft[] {
    return goals.map((goal) => ({ title: goal.title, target: goal.target ?? "" }));
}

/**
 * The person's own form: their rating, their note, and their goals.
 *
 * A goal removed here is removed on save - the server replaces the list, because a
 * goal the person no longer claims must not linger. The form is read-only once the
 * reviewer has rated it (`409` from the server), and the screen says so instead of
 * offering buttons that would fail.
 */
function SelfForm({
    row,
    canSelf,
    busy,
    onSave,
    onSubmit,
}: {
    row: AppraisalRow;
    canSelf: boolean;
    busy: string | null;
    onSave: (input: SelfAssessmentInput) => Promise<boolean>;
    onSubmit: () => Promise<boolean>;
}) {
    const [rating, setRating] = useState(row.selfRating ?? 3);
    const [note, setNote] = useState(row.selfNote ?? "");
    const [goals, setGoals] = useState<GoalDraft[]>(goalDrafts(row.goals));

    const locked = row.status === "Reviewed" || row.status === "Finalized";
    const editable = canSelf && !locked;

    async function save() {
        await onSave({
            selfRating: rating,
            selfNote: note.trim() || null,
            goals: goals
                .filter((goal) => goal.title.trim().length > 0)
                .map((goal) => ({
                    title: goal.title.trim(),
                    target: goal.target.trim() || null,
                })),
        });
    }

    return (
        <Card>
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <b>My appraisal</b>{" "}
                    <span className="text-muted-foreground text-xs">{row.cycleName}</span>
                </div>
                <Badge tone={TONE[row.status]}>{row.statusLabel}</Badge>
            </div>

            <p className="text-muted-foreground mt-1 text-xs">
                {locked
                    ? "The reviewer has recorded a rating, so this is now the record of what you said - it cannot be edited."
                    : "Rate your own year, note what happened, and list the goals you want to be judged against."}
            </p>

            <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <label className="text-sm">
                    <span className="text-muted-foreground block text-xs">My rating</span>
                    <Select
                        aria-label="My rating"
                        value={String(rating)}
                        disabled={!editable}
                        onChange={(event) => setRating(Number(event.target.value))}
                    >
                        {RATINGS.map((value) => (
                            <option key={value} value={value}>
                                {value} / 5
                            </option>
                        ))}
                    </Select>
                </label>
                <label className="text-sm">
                    <span className="text-muted-foreground block text-xs">Reviewer</span>
                    <div className="pt-2 text-sm">
                        {row.reviewerName ?? "—"}
                        {row.reviewerRating !== null && ` · ${row.reviewerRating}/5`}
                    </div>
                </label>
            </div>

            <label className="mt-2 block text-sm">
                <span className="text-muted-foreground block text-xs">My note</span>
                <Textarea
                    aria-label="My note"
                    rows={3}
                    value={note}
                    disabled={!editable}
                    onChange={(event) => setNote(event.target.value)}
                />
            </label>

            <div className="mt-3">
                <span className="text-muted-foreground text-xs">Goals</span>
                {goals.length === 0 && (
                    <p className="text-muted-foreground text-xs">No goals yet.</p>
                )}
                {goals.map((goal, index) => (
                    <div key={index} className="mt-1 flex flex-wrap items-center gap-2">
                        <Input
                            aria-label={`Goal ${index + 1}`}
                            placeholder="What you set out to do"
                            value={goal.title}
                            disabled={!editable}
                            onChange={(event) =>
                                setGoals((current) =>
                                    current.map((item, position) =>
                                        position === index
                                            ? { ...item, title: event.target.value }
                                            : item,
                                    ),
                                )
                            }
                        />
                        <Input
                            aria-label={`Target ${index + 1}`}
                            placeholder="What done looks like"
                            value={goal.target}
                            disabled={!editable}
                            onChange={(event) =>
                                setGoals((current) =>
                                    current.map((item, position) =>
                                        position === index
                                            ? { ...item, target: event.target.value }
                                            : item,
                                    ),
                                )
                            }
                        />
                        {editable && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                    setGoals((current) =>
                                        current.filter((_, position) => position !== index),
                                    )
                                }
                            >
                                Remove
                            </Button>
                        )}
                    </div>
                ))}
                {editable && (
                    <Button
                        variant="outline"
                        size="sm"
                        className="mt-2"
                        onClick={() =>
                            setGoals((current) => [...current, { title: "", target: "" }])
                        }
                    >
                        Add goal
                    </Button>
                )}
            </div>

            {editable && (
                <div className="mt-3 flex flex-wrap gap-2">
                    <Button loading={busy === "self"} onClick={() => void save()}>
                        Save
                    </Button>
                    <Button
                        variant="outline"
                        loading={busy === "submit"}
                        disabled={row.status !== "Draft"}
                        onClick={() => void onSubmit()}
                    >
                        {row.status === "Draft" ? "Submit to reviewer" : "Submitted"}
                    </Button>
                </div>
            )}
        </Card>
    );
}

/** The reviewer's dialog: a rating, a note, and a verdict on each goal. */
function ReviewDialog({
    row,
    busy,
    onClose,
    onReview,
    onJudge,
}: {
    row: AppraisalRow;
    busy: string | null;
    onClose: () => void;
    onReview: (input: ReviewInput) => Promise<boolean>;
    onJudge: (goalId: string, achieved: boolean) => Promise<boolean>;
}) {
    const [rating, setRating] = useState(row.reviewerRating ?? row.selfRating ?? 3);
    const [note, setNote] = useState(row.reviewerNote ?? "");

    return (
        <Modal open title={`Review · ${row.name}`} onClose={onClose}>
            <p className="text-muted-foreground text-sm">
                Their own words: {row.selfRating === null ? "no rating" : `${row.selfRating}/5`}
                {row.selfNote ? ` - “${row.selfNote}”` : ""}
            </p>

            <label className="mt-3 block text-sm">
                <span className="text-muted-foreground block text-xs">Your rating</span>
                <Select
                    aria-label="Reviewer rating"
                    value={String(rating)}
                    onChange={(event) => setRating(Number(event.target.value))}
                >
                    {RATINGS.map((value) => (
                        <option key={value} value={value}>
                            {value} / 5
                        </option>
                    ))}
                </Select>
            </label>

            <label className="mt-2 block text-sm">
                <span className="text-muted-foreground block text-xs">Your note</span>
                <Textarea
                    aria-label="Reviewer note"
                    rows={3}
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                />
            </label>

            <div className="mt-3">
                <span className="text-muted-foreground text-xs">Goals</span>
                {row.goals.length === 0 && (
                    <p className="text-muted-foreground text-xs">
                        No goals were set - the rating is the whole conversation.
                    </p>
                )}
                {row.goals.map((goal) => (
                    <div
                        key={goal.id}
                        className="mt-1 flex flex-wrap items-center justify-between gap-2 rounded-md border p-2"
                    >
                        <div style={{ lineHeight: 1.25 }}>
                            <div className="text-sm">{goal.title}</div>
                            {goal.target && (
                                <div className="text-muted-foreground text-xs">{goal.target}</div>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            <Badge
                                tone={
                                    goal.achieved === null
                                        ? "muted"
                                        : goal.achieved
                                          ? "green"
                                          : "red"
                                }
                            >
                                {goal.achieved === null
                                    ? "Not judged"
                                    : goal.achieved
                                      ? "Achieved"
                                      : "Missed"}
                            </Badge>
                            <Button
                                variant="ghost"
                                size="sm"
                                disabled={busy !== null}
                                onClick={() => void onJudge(goal.id, true)}
                            >
                                ✓
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                disabled={busy !== null}
                                onClick={() => void onJudge(goal.id, false)}
                            >
                                ✗
                            </Button>
                        </div>
                    </div>
                ))}
            </div>

            <div className="mt-4 flex justify-end gap-2">
                <Button variant="ghost" onClick={onClose}>
                    Close
                </Button>
                <Button
                    loading={busy === "review"}
                    onClick={async () => {
                        const saved = await onReview({
                            reviewerRating: rating,
                            reviewerNote: note.trim() || null,
                        });
                        if (saved) onClose();
                    }}
                >
                    Save rating
                </Button>
            </div>
        </Modal>
    );
}

/**
 * The appraisal season's screen: which season, my own form, and the queue.
 *
 * Three things it refuses to do:
 *
 * * **show a queue it cannot read.** The server scopes it - a teacher-only account
 *   sees their own row; the season controls appear only with `appraisals.manage`;
 * * **offer a write the row will refuse.** `Review` appears only once the person has
 *   submitted, `Finalize` only once it is reviewed - and a finalised row offers
 *   nothing at all;
 * * **treat an unjudged goal as missed.** It prints `not judged`, not `0 of 3`.
 */
export default function AppraisalTab({
    canSelf,
    canReview,
    canManage,
}: {
    canSelf: boolean;
    canReview: boolean;
    canManage: boolean;
}) {
    const a = useAppraisal({ canRead: true, canManage });
    const [seasonOpen, setSeasonOpen] = useState(false);
    const [reviewing, setReviewing] = useState<AppraisalRow | null>(null);
    const [name, setName] = useState("");
    const [start, setStart] = useState(`${new Date().getFullYear()}-04-01`);
    const [end, setEnd] = useState(`${new Date().getFullYear() + 1}-03-31`);

    const queue = a.queue;
    const cycle = queue?.cycle ?? null;

    const columns = [
        {
            key: "name",
            header: "Teacher",
            render: (row: AppraisalRow) => (
                <div style={{ lineHeight: 1.2 }}>
                    <div>{row.name}</div>
                    <div className="text-muted-foreground text-[0.74rem]">
                        {row.employeeCode || row.department}
                    </div>
                </div>
            ),
        },
        {
            key: "status",
            header: "State",
            render: (row: AppraisalRow) => <Badge tone={TONE[row.status]}>{row.statusLabel}</Badge>,
        },
        {
            key: "ratings",
            header: "Self / Reviewer",
            render: (row: AppraisalRow) => (
                <span className="text-sm">
                    {row.selfRating ?? "—"} / {row.reviewerRating ?? "—"}
                </span>
            ),
        },
        {
            key: "goals",
            header: "Goals",
            render: (row: AppraisalRow) =>
                row.goalsTotal === 0 ? (
                    <span className="text-muted-foreground text-xs">none</span>
                ) : (
                    <span className="text-sm">
                        {row.goalsAchieved} met · {row.goalsJudged - row.goalsAchieved} missed ·{" "}
                        {row.goalsTotal - row.goalsJudged} not judged
                    </span>
                ),
        },
        {
            key: "actions",
            header: "",
            render: (row: AppraisalRow) => (
                <div className="flex gap-2">
                    {canReview && row.status !== "Draft" && row.status !== "Finalized" && (
                        <Button
                            variant="ghost"
                            size="sm"
                            disabled={a.busy !== null}
                            onClick={() => setReviewing(row)}
                        >
                            Review
                        </Button>
                    )}
                    {canManage && row.status === "Reviewed" && (
                        <Button
                            variant="ghost"
                            size="sm"
                            disabled={a.busy !== null}
                            onClick={() => void a.finalize(row.id)}
                        >
                            Finalize
                        </Button>
                    )}
                </div>
            ),
        },
    ];

    return (
        <div>
            <div className="toolbar">
                <Select
                    aria-label="Season"
                    value={a.cycleId ?? ""}
                    onChange={(event) => a.setCycleId(event.target.value)}
                >
                    {a.cycles.length === 0 && <option value="">No season yet</option>}
                    {a.cycles.map((row) => (
                        <option key={row.id} value={row.id}>
                            {row.name} · {row.status}
                        </option>
                    ))}
                </Select>

                {cycle !== null && (
                    <Badge tone={cycle.status === "Open" ? "green" : "muted"}>
                        {cycle.appraisals} people · {cycle.finalized} finalised
                    </Badge>
                )}

                {canManage && (
                    <>
                        <Button variant="outline" onClick={() => setSeasonOpen(true)}>
                            New season
                        </Button>
                        {cycle !== null && (
                            <Button
                                variant="outline"
                                loading={a.busy === "move"}
                                onClick={() =>
                                    void a.moveCycle(
                                        cycle.status === "Draft"
                                            ? "Open"
                                            : cycle.status === "Open"
                                              ? "Closed"
                                              : "Open",
                                    )
                                }
                            >
                                {cycle.status === "Draft"
                                    ? "Open season"
                                    : cycle.status === "Open"
                                      ? "Close season"
                                      : "Reopen"}
                            </Button>
                        )}
                    </>
                )}
                {a.refreshing && <span className="text-muted-foreground text-xs">Updating…</span>}
            </div>

            {a.loading && <Spinner size="md" />}

            {!a.loading && a.error !== null && (
                <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                    {errorMessage(a.error, "The appraisal season could not be loaded.")}
                </p>
            )}

            {a.writeError !== null && (
                <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                    {errorMessage(a.writeError, "That change was not saved.")}
                </p>
            )}

            {!a.loading && cycle === null && (
                <Card>
                    <p className="text-muted-foreground text-sm">
                        No appraisal season yet. The office creates one and then opens it - opening
                        it gives every person on the roll an appraisal to fill in.
                    </p>
                </Card>
            )}

            {!a.loading && queue !== null && (
                <>
                    {queue.mine !== null ? (
                        <div style={{ marginBottom: "0.75rem" }}>
                            <SelfForm
                                key={`${queue.mine.id}-${queue.mine.status}-${queue.mine.goalsTotal}`}
                                row={queue.mine}
                                canSelf={canSelf}
                                busy={a.busy}
                                onSave={(input) => a.saveSelf(queue.mine!.id, input)}
                                onSubmit={() => a.submit(queue.mine!.id)}
                            />
                        </div>
                    ) : (
                        <Card>
                            <p className="text-muted-foreground text-sm">
                                You have no appraisal in this season - only people on the teaching
                                roll are appraised.
                            </p>
                        </Card>
                    )}

                    <Table
                        columns={columns}
                        rows={queue.rows}
                        rowKey={(row) => row.id}
                        empty="Nobody is on the appraisal roll for this season yet."
                    />

                    <p className="text-muted-foreground mt-2 text-xs">
                        A goal nobody has judged is <b>not</b> a missed goal. Finalising an
                        appraisal locks it: no write is accepted afterwards, not even the
                        reviewer&apos;s.
                    </p>
                </>
            )}

            <Modal
                open={seasonOpen}
                title="New appraisal season"
                onClose={() => setSeasonOpen(false)}
            >
                <div className="grid gap-2">
                    <label className="text-sm">
                        <span className="text-muted-foreground block text-xs">Name</span>
                        <Input
                            aria-label="Season name"
                            placeholder="2026-27 Annual"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                        />
                    </label>
                    <div className="grid gap-2 sm:grid-cols-2">
                        <label className="text-sm">
                            <span className="text-muted-foreground block text-xs">From</span>
                            <Input
                                type="date"
                                aria-label="Season starts"
                                value={start}
                                onChange={(event) => setStart(event.target.value || todayISO())}
                            />
                        </label>
                        <label className="text-sm">
                            <span className="text-muted-foreground block text-xs">To</span>
                            <Input
                                type="date"
                                aria-label="Season ends"
                                value={end}
                                onChange={(event) => setEnd(event.target.value || todayISO())}
                            />
                        </label>
                    </div>
                </div>

                <div className="mt-4 flex justify-end gap-2">
                    <Button variant="ghost" onClick={() => setSeasonOpen(false)}>
                        Cancel
                    </Button>
                    <Button
                        loading={a.busy === "cycle"}
                        disabled={name.trim().length < 3}
                        onClick={async () => {
                            const ok = await a.createCycle({
                                name: name.trim(),
                                startDate: start,
                                endDate: end,
                            });
                            if (ok) {
                                setName("");
                                setSeasonOpen(false);
                            }
                        }}
                    >
                        Create
                    </Button>
                </div>
            </Modal>

            {reviewing !== null && (
                <ReviewDialog
                    key={reviewing.id}
                    row={reviewing}
                    busy={a.busy}
                    onClose={() => setReviewing(null)}
                    onReview={(input) => a.review(reviewing.id, input)}
                    onJudge={(goalId, achieved) => a.judgeGoal(goalId, achieved)}
                />
            )}
        </div>
    );
}
