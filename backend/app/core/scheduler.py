"""The school's background jobs - one daemon thread, one tick a minute.

Why a thread and not a dependency
---------------------------------
The only job the product needs today is the exam reminder (Phase 7): "today's paper is
tomorrow, tell the class". That is one query a minute at worst. APScheduler would add a
dependency, a config surface and an admin UI that nobody asked for, so the solver is the
smallest thing that can be *stopped*: a loop that wakes every `TICK_SECONDS`, runs the
registered jobs, logs a failure and carries on.

Design notes worth keeping
--------------------------
* **A job never kills the scheduler.** Each call is wrapped; an exception is logged with
  the job's name and the next tick still happens.
* **`run_once()` is the seam the tests use** - the thread is not started in tests, so
  nothing has to be mocked to prove a job ran or that a failing job is swallowed.
* **Jobs get their own session**, opened and closed inside the tick: a job that leaves a
  transaction open would hold a pooled connection for the life of the process.
* Registering is explicit (`register_job`), so "what runs in the background" is a short
  list somebody can read instead of a decorator that scatters it.
"""

import logging
import threading
from collections.abc import Callable

from sqlmodel import Session

from app.core.db import engine

logger = logging.getLogger("eduverse.scheduler")

#: How often the loop wakes. A minute is the product's clock: the reminder goes out on
#: the minute, nothing else is time-critical.
TICK_SECONDS = 60

#: (name, callable) - `callable(session)`; read it, it is the whole schedule.
JOBS: list[tuple[str, Callable[[Session], object]]] = []


def register_job(name: str, job: Callable[[Session], object]) -> None:
    """Add a job to the schedule (idempotent by name - a re-import must not double it)."""
    if any(existing == name for existing, _ in JOBS):
        return
    JOBS.append((name, job))
    logger.info("scheduler: registered %s", name)


def run_once() -> int:
    """Run every registered job once, in its own session. Returns how many succeeded."""
    done = 0
    for name, job in list(JOBS):
        try:
            with Session(engine) as session:
                job(session)
            done += 1
        except Exception as error:
            logger.warning("scheduler: job %s failed: %s", name, error)
    return done


class Scheduler:
    """A start/stop handle around the tick. One instance is used by the app."""

    def __init__(self, tick_seconds: int = TICK_SECONDS) -> None:
        self.tick_seconds = tick_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start ticking. Calling it twice is safe - the second call is a no-op."""
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="eduverse-scheduler", daemon=True
        )
        self._thread.start()
        logger.info(
            "scheduler: started (%s job(s), every %ss)", len(JOBS), self.tick_seconds
        )

    def stop(self) -> None:
        """Ask the loop to finish and wait for it (short - the tick checks often)."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.tick_seconds)
        self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            run_once()
            self._stop.wait(self.tick_seconds)


#: The one scheduler the application starts in `lifespan`.
scheduler = Scheduler()
