"""The daily staff register - who was at school on a given day.

`employee` says who is on the roll and `leaverequest` says who is away; neither
says whether somebody actually turned up. This sub-feature is that one fact, kept
per person per day:

* **one row per person per day** (`UNIQUE(school_id, employee_id, date)`), because
  "present and also absent on Tuesday" is not a thing a register may hold;
* **approved leave is derived, never copied.** A person on an approved leave shows
  `On Leave` without a row here. Copying the leave into this table would mean
  rewriting the register every time a leave is approved, rejected or shortened,
  and the two copies would eventually disagree about the same Tuesday;
* **no row is not "absent"**. It is `Not Marked`, which is what the screen prints,
  because a month nobody has marked must not read as a month of absences.

The percentage the month view prints divides by the days **somebody marked**
(`labels.attendance_percent`), so an unfinished month is reported as unfinished
rather than as an attendance problem.

`models.py` is registered in `app/core/schema.py`, so the table is created with
everything else, and every write is appended to `staffauditlog` under the
`attendance` section.
"""
