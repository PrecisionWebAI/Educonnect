"""The Teachers & Staff hub's router: the directory plus every sub-feature.

Mount order is the whole point of this file. FastAPI tries the routes in the order
they were added, and the hub's own router ends with `/{teacher_id}` - a path that
would happily accept "profile" as an id. So the sub-features come **first** and the
catch-all last.

The prefix lives here rather than in `people/api.py` because a router cannot be
included with an empty prefix **and** an empty path (the directory is
`@router.get("")`): the segment has to be spelled out on the include that carries
it. `people/api.py` therefore mounts this router as it is.

Later phases add their folders here the same way (`substitution`, `appraisal`),
with the same rule: a fixed path never sits behind a variable one.
"""

from fastapi import APIRouter

from .appraisal.performance import router as performance
from .appraisal.router import router as appraisal
from .profile.router import router as profile
from .router import router as teachers
from .staff_attendance.router import router as staff_attendance
from .substitution.router import router as substitution
from .workload.router import router as workload

router = APIRouter()
#: `GET /teachers/performance` keeps its URL: it is spelled out inside the router, so
#: it is included with **no** prefix (an empty prefix with a real path is fine; the
#: reverse is what FastAPI refuses).
router.include_router(performance, tags=["Staff performance"])
router.include_router(
    staff_attendance, prefix="/teachers/attendance", tags=["Staff attendance"]
)
router.include_router(workload, prefix="/teachers/workload", tags=["Staff workload"])
router.include_router(
    substitution, prefix="/teachers/substitutions", tags=["Staff substitution"]
)
router.include_router(
    appraisal, prefix="/teachers/appraisals", tags=["Staff appraisal"]
)
router.include_router(profile, prefix="/teachers/profile", tags=["Staff profile"])
router.include_router(teachers, prefix="/teachers", tags=["Teachers"])
