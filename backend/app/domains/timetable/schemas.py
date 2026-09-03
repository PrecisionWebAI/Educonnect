from .models import TimetablePeriodBase


class TimetablePeriodCreate(TimetablePeriodBase):
    pass


class TimetablePeriodRead(TimetablePeriodBase):
    id: int
