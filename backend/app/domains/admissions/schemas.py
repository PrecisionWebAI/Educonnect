import datetime
from typing import Literal

from pydantic import BaseModel

from .models import AdmissionApplicationBase


class AdmissionApplicationCreate(AdmissionApplicationBase):
    """Body accepted by the Admission form.

    Every field is optional on purpose: the same endpoint stores a half-filled
    draft *and* a completed registration. `application_no` is assigned by the
    server when the client does not send one.
    """


class SeparationRecordRead(BaseModel):
    """The separation block as one object (see `AdmissionApplication.separation`)."""

    dropped_class: str | None = None
    reason: str | None = None
    session: str | None = None
    # Annotated as `datetime.date`, not `date`: the field itself is called
    # `date`, and a bare `date | None` would be resolved against that field.
    date: datetime.date | None = None


class AdmissionApplicationRead(AdmissionApplicationBase):
    id: int
    separation: SeparationRecordRead | None = None


class SeparationRecordWrite(BaseModel):
    """Body of `PUT /admissions/applications/{application_id}/separation`."""

    reason: str
    session: str
    date: datetime.date
    dropped_class: str | None = None


class AdmissionApplicationUpdate(AdmissionApplicationBase):
    """Body of `PUT /admissions/applications/{application_id}` (full row)."""


class AdmissionStatusUpdate(BaseModel):
    status: Literal["Draft", "Registered"]
    notes: str | None = None
