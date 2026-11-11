"""Academic - the classroom group: classes, students, attendance, marks, exams.

`academic/classroom/` is the hub the rest of the school hangs off, so every
feature the Classroom screen opens (student list, attendance, homework,
timetable, exams and the AI paper builder) sits inside it.

The group router is `api.py`, not this file: importing `academic.classroom.
students.models` must never build routers (that import runs this package first),
and a package `__init__` that mounts routes turns any model import into a
bootstrap cycle.
"""
