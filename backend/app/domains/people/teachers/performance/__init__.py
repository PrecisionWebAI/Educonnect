"""Teacher performance, measured from facts the school already records.

The appraisal season is gone, and with it the score that averaged anonymous star
ratings with a syllabus percentage. This package replaces it with three ingredients,
each of which carries a date and can be checked:

* **attendance** - the staff register over the session;
* **workload** - timetable periods against the school's own capacity rule;
* **course** - the chapter plan: how much is covered, and how much landed on time.

`service.py` owns the calculation, `router.py` owns the one route. Nothing here
stores a score: a stored number is true on the day a job ran, and the first question
a principal asks is "does this include last week?".
"""
