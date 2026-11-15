# phase2.md — pointer only (Classroom module)

**Read `backend/phase.md` first.** It is the single tracker: Phase 0 audit + the
checked plan for Phases 1–10.

This file exists only as the reminder the owner asked for ("wo complete in further
task in further phase, jaise pehle kiya tha"). It holds no plan of its own.

## Where we are

| | |
| --- | --- |
| Phase done | **6 — Course tab UI** (result in `phase.md`) |
| Phase next | **7 — Exams schema + backend** (starts only when the owner writes **"next phase"**) |
| Phases after | 2 Attendance backend · 3 Notifications · 4 Attendance UI + leave · 5 Course backend · 6 Course UI · 7 Exams backend · 8 Exams UI · 9 Homework + Timetable · 10 Rename + final verification |

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
* **Owner decision (15 Nov 2026): `examsubject` and `syllabusprogress` are dropped**, not
  kept as mirrors. `syllabusprogress` goes in Phase 5's migration, `examsubject` in
  Phase 7's; each counts its rows first and aborts printing the count if it is not 0,
  each downgrade recreates the empty table (`up → down → up` proven), and every model,
  read, seed and test that names them is removed in that phase. New data goes only to
  `chapter` / `chapter_progress` and `exam_paper` / `exam_paper_chapter` / `marks`;
  course completion is computed from `chapter_progress` only (also the Teachers score).
* Tab order: **Students · Attendance · Course · Exams · Homework · Timetable · AI Papers**.
* Do not change AI Papers behaviour (a separate task owns it).

