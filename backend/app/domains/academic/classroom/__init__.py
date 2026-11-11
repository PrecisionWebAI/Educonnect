"""Classroom - the hub the rest of the school hangs off.

`GET /classroom/overview` returns one group per class, each with a card per
class-section. Every number is aggregated from the real tables (students,
attendance, timetable, homework, diary, fees, marks, syllabus progress) so the
screen shows what the school actually has.

This package is also the group router for the Classroom screen's own features: the
catalog (`academics`), the student list, attendance, homework, the timetable and
exams (with the AI paper builder) are all mounted from `api.py` - not from here,
so that importing a model module never builds a router.
"""
