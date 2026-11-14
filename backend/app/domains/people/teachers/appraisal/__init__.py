"""Appraisal: the season, one person's appraisal in it, goals, and training.

The season is a **window**, the appraisal is **one person inside one window**, and the
rating is a number a school can defend: 1-5, given twice - once by the person, once by
their reviewer - and then locked when the office finalises it.

Four decisions worth the reader's time:

* **a row exists for everybody on the roll**, created when the season opens, so
  "who have we not appraised yet?" is answerable. A season built from whoever filled
  a form cannot answer its own question;
* **three rights, three people.** The appraisee fills in `/self` and `/submit`; an HOD
  (their department) or the office reviews; the office opens the season and finalises.
  A reviewer who could finalize would make the lock decorative;
* **finalising is the end.** Every write on a finalized appraisal is `409`, including
  the reviewer's: the number has been told to somebody;
* **a goal is judged, not assumed.** `achieved` is `bool | None`, and `None` (nobody
  has looked) is not "failed" - the same rule the leave balance follows for `0`.

`teacherreview` (the anonymous star ratings) is a *different* claim about the same
teacher and is deliberately not merged in: averaging an anonymous parent's score with
a signed appraisal is how a school ends up defending a number nobody wrote.
"""
