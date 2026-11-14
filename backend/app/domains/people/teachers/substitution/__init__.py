"""Substitution: who is away, which periods that leaves empty, and who stands in.

The feature answers one question the timetable asks every morning - *somebody is
away, who covers their periods?* - and it answers it from data the school already
has: the approved leave (Phase 6), the timetable (`timetableperiod`), and the
subjects each teacher can take (`teachersubject`). Nothing is copied into a new
"current timetable" table, so a period moved at 08:00 moves the cover list with it.

Three design decisions worth the reader's time:

* **the board is derived and writes nothing.** Opening the screen is a `GET`; rows
  are created only when cover is arranged, signed or withdrawn;
* **the substitute is chosen with a reason, not a hidden score.** `engine` filters by
  what makes cover *possible* (teaches the subject, is here, is free at that hour)
  and then ranks by what makes it *sensible* (same department, knows the class,
  lighter load) - and it says which, in words, for every candidate and every
  refusal;
* **a withdrawn cover is deleted, not cancelled.** The slot is held by
  `UNIQUE(school, period, date)`; a cancelled row would keep the room's one adult
  occupied and block the replacement.

The tables are `substitutionrequest` (the absence) and `substitutionassignment` (the
cover); the vocabulary is in `people/teachers/labels.py`.
"""
