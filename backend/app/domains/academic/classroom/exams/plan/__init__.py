"""The Exams plan package.

Importing it has one side effect, on purpose: the **exam reminder** is registered on the
Phase 3 scheduler, so "the paper is tomorrow" goes out without any screen being opened.
Registration is idempotent by name (`scheduler.register_job`), so a re-import cannot
schedule it twice.
"""

from app.core.scheduler import register_job

from .service import reminder_job

register_job("exam-reminder", reminder_job)
