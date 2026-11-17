# phase2.md — pointer only (Classroom module)

**Read `backend/phase.md` first.** It is the single tracker: Phase 0 audit + the
checked plan for Phases 1–10.

This file exists only as the reminder the owner asked for ("wo complete in further
task in further phase, jaise pehle kiya tha"). It holds no plan of its own.

## Where we are

| | |
| --- | --- |
| Phase done | **10 — Rename, cleanup, final verification** (result in `phase.md`; the Classroom module is complete) |
| Phase next | — (10 was the last. What is left is outside the plan: the owner's appraisal decision — drop the tables or keep them — and the Phase 4/6 inline-style restyle) |
| Phases after | — |

> **Frontend note (owner, 16 Nov 2026):** the UI overhaul ("usi theme change") landed on
> `development` after Phase 6. Every frontend file from Phase 8 on is written against
> **that** theme - `PageHeader`'s `app-page-banner`, `Table`'s `app-data-table`,
> `glass-tile` surfaces, `text-muted-foreground` / `bg-primary/10` tokens instead of inline
> `var(--muted)` styles, `Tabs`'s `className`, lucide icons - and the tab descriptions in
> `SectionDetailPage` (`TAB_DESCRIPTIONS`). The Exams tab (Phase 8) was written that way.
> The Phase 4/6 components still compile and render (checked with `tsc`) and keep their
> inline colours for now - the restyle is the one open item on the Phase 8 checklist.

## How to resume (every phase, in this order)

1. Open `backend/phase.md`, read the Phase 0 result and the checklist for the phase
   in progress.
2. Take the **first unticked** `- [ ]` item of that phase; finish the phase fully
   (code + migration with a working downgrade + tests), tick items as they land, and
   write a short note whenever reality differs from the plan.
3. Run the gates in the container (host Python is blocked by machine policy):

   ```
   docker build --target checks -t eduverse-checks .        # from backend/
   docker run --rm -v "<repo>/backend:/src" -w /src -e PYTHONPATH=/src \
     eduverse-checks python -m pytest tests -q
   docker run --rm -v "<repo>/backend:/src" -w /src \
     eduverse-checks python -m ruff check .
   ```

4. Prove every new migration `up → down → up` and paste the output into `phase.md`.
5. Add a dated **Result** block at the end of that phase in `phase.md` (summary,
   files/tables touched, migrations, tests, open questions, plan for the next phase),
   then send the short report and **stop** until the owner writes "next phase".

## Standing rules (short)

* One source of truth; `school_id NOT NULL` + filtered reads; server-side permission
  with the same codename in the UI; DB reads/writes only (no synthetic numbers, no
  cache-only writes); no hard-deletes of people; constraint violations → 4xx;
  money **and marks** are `numeric`; every rule has a test with a refusal case;
  notifications never block or roll back the main action.
* Never edit an old migration. Never drop a column/table without the owner's approval.
* **Owner decision (15 Nov 2026) — done:** `syllabusprogress` was dropped in Phase 5
  (`d3f1a8c5e2b7`) and `examsubject` in Phase 7 (`e4b7c2d9a1f6`); each counted its rows
  first, aborted printing the count when non-zero, recreated the empty table on
  downgrade, and proved `up → down → up`. Every model, read, seed and test that named
  them is gone. New data goes only to `chapter` / `chapter_progress` and `exam_paper` /
  `exam_paper_chapter` / `marks` / `marks_audit` / `grade_scale`; course completion is
  computed from `chapter_progress` only (also the Teachers score), and a paper's maximum
  lives only on `exam_paper`.
* Tab order: **Students · Attendance · Course · Exams · Homework · Timetable · AI Papers**.
* Do not change AI Papers behaviour (a separate task owns it).

