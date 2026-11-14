"""How full a teacher's week is, and what fills it.

The hub (`people/teachers/`) answers "who is on the roll" and already prints a
load per person. This sub-feature answers the three questions that load cannot:

* **what is a full week?** - `staffworkloadrule`, one row per school. Without it
  the matrix divided a teacher's periods by however many slots the timetable
  happened to contain, so "80% utilised" changed meaning the day somebody added
  a period to Class 6;
* **what else does the week hold?** - `staffduty`: exam invigilation, gate duty,
  assembly, the library desk. Not periods (nobody teaches them) and not leave
  (they are not away), so they belong in neither existing table;
* **what does one person's week look like?** - the grid the drawer draws from
  `timetableperiod` plus those duties.

Duties are **counted, never converted**. Turning a gate duty into "1.5 periods"
would need a weight the school never agreed, and a utilisation figure nobody can
reproduce is worse than two honest numbers side by side.

`models.py` is registered in `app/core/schema.py`, so the tables are created with
everything else.
"""
