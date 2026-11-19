"""The Course tab's backend: the plan, who teaches it, and how far each section has got."""

from app.core.scheduler import register_job

from .reminders import remind_unsubmitted

# Same pattern as `exams/plan/__init__.py`: importing the package is what schedules the
# job, so `main.py` does not need a second list to keep in sync.
register_job("course.reminders", remind_unsubmitted)
