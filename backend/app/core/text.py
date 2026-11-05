"""Canonical text - the database stores lowercase, the UI decides how it looks.

Every value a router writes passes through :class:`CanonicalRequest`, which
lower-cases stored text: a name, an email, a phone number, a class name, a
religion. One row can then never disagree with another about case, "Tanya " and
"tanya" are the same value, and a lookup that compares what a client typed with
what is already stored cannot miss. Presentation is the frontend's job
(`lib/format.ts` → `titleCase`), so no screen ever shows the stored form.

What is deliberately **not** touched:

* **Secrets** - a password or a token must keep its case to be valid.
* **Prose** - notes, reasons, descriptions, questions, messages. A paragraph has
  no canonical form and lower-casing it would corrupt meaning, not tidy it.
* **Links** - a URL path is case-sensitive; lower-casing it can 404.
* **Codes** - `application_no`, `employee_code`, `ifsc`, `admission_number` ...
  are identifiers people read aloud, not names to be normalised.
* **Fixed vocabularies** - `status`, `priority`, `session`, `needs_transport`
  and friends store the exact wording the screen shows ("Draft", "Yes"), and
  the workflow compares those strings. They are also skipped automatically when
  the field is typed as `Literal[...]` or an `Enum`.

A **phone number** is not lower-cased, it is reduced to its digits: the database
holds `9876543210`, so "+91 98765 43210" and "098765 43210" are the same number
and a school can ring the value it read off the form. Whether a number is
*required*, and that it must be exactly ten digits, is checked by the service
that owns the record (`admissions/service.py`, `staff/service.py`) - the same
place the rest of that record's rules live.

Used by request schemas only: a *response* model must hand back what is stored
(and its notes are prose), so `Read` models stay plain `BaseModel`.
"""

from __future__ import annotations

import enum
import re
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel, model_validator

#: A field whose name contains one of these keeps its case. Matched as a
#: substring of the lower-cased field name, so `student_email` is canonical but
#: `ifsc_code` is not.
KEEP_CASE: tuple[str, ...] = (
    # --- secrets ----------------------------------------------------------
    "password",
    "token",
    "secret",
    "hash",
    "otp",
    "api_key",
    "signature",
    # --- prose ------------------------------------------------------------
    "notes",
    "note",
    "reason",
    "description",
    "content",
    "answer",
    "question",
    "explanation",
    "rationale",
    "remark",
    "comment",
    "feedback",
    "message",
    "summary",
    "instruction",
    "prompt",
    "text",
    "title",
    "topic",
    "chapter",
    "activity",
    "statement",
    "body",
    "reply",
    "label",
    "assignee",
    # --- links / files ----------------------------------------------------
    "url",
    "link",
    "path",
    "file",
    "image",
    "photo",
    "avatar",
    # --- identifiers and codes -------------------------------------------
    "code",
    "number",
    "_no",
    "isbn",
    "plate",
    "fingerprint",
    "ifsc",
    "pan_no",
    "aadhaar",
    "unique_id",
    "emp_id",
    # --- fixed vocabularies the workflow compares -------------------------
    "status",
    "priority",
    "severity",
    "role",
    "type",
    "mode",
    "qtype",
    "kind",
    "tone",
    "session",
    "needs_",
    "day",
    "month",
    "term",
    "grade",
    "stage",
    "qualification",
)


def _keeps_case(field_name: str) -> bool:
    """True when this field is exempt from canonicalisation (see `KEEP_CASE`)."""
    lowered = field_name.lower()
    return any(part in lowered for part in KEEP_CASE)


def _is_fixed_choice(annotation: Any) -> bool:
    """True for `Literal[...]` / `Enum` fields - their values are fixed tokens."""
    if annotation is None:
        return False
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return True
    if get_origin(annotation) is Literal:
        return True
    return any(
        _is_fixed_choice(argument)
        for argument in get_args(annotation)
        if argument is not type(None)
    )


def canonical(value: str | None) -> str | None:
    """The stored form of one piece of text: trimmed, lower-cased, empty as None.

    Used by the service layer where a value is *built* rather than received
    (a login candidate, a class-section label) so it matches what the request
    path would have stored.
    """
    if value is None:
        return None
    text = value.strip()
    return text.lower() if text else None


#: How many digits a phone number has. A school rings the number it read off the
#: form, so the database holds exactly this many - no spaces, no "+91".
PHONE_DIGITS = 10

#: Field names that hold a phone number (`guardian_phone`, `phone`, `mobile`).
#: `emergency_contact` is deliberately not one of them: that field may hold a
#: name with a number after it.
_PHONE_FIELD_PARTS = ("phone", "mobile")


def _is_phone_field(field_name: str) -> bool:
    """True when this field holds a phone number (see `_PHONE_FIELD_PARTS`)."""
    lowered = field_name.lower()
    return any(part in lowered for part in _PHONE_FIELD_PARTS)


def phone_digits(value: str) -> str:
    """The digits of a phone number, however it was typed.

    Formatting - spaces, dashes, brackets, a leading "+" - is dropped, and so is
    the country / trunk prefix: "+91 98765 43210", "098765 43210" and
    "9876543210" all come back as "9876543210". A value that is not a ten-digit
    number comes back as whatever digits it had, so the caller can reject it and
    say how many it found.
    """
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    return digits


def canonical_phone(value: str | None) -> str | None:
    """The stored form of a phone number: its ten digits, or None when empty."""
    if value is None:
        return None
    return phone_digits(value) or None


def phone_problem(value: str | None, label: str = "the phone number") -> str | None:
    """Why this phone number cannot be stored, or None when it is fine.

    Empty is **not** a problem here: whether a number is required is the caller's
    rule (`REQUIRED_TO_REGISTER`, `REQUIRED_TO_HIRE`). This only judges the shape,
    so the office is told "must be exactly 10 digits" rather than a bare refusal.
    """
    if not value or not value.strip():
        return None
    digits = phone_digits(value)
    if len(digits) != PHONE_DIGITS:
        return (
            f"{label} must be exactly {PHONE_DIGITS} digits - "
            f"'{value.strip()}' has {len(digits)}."
        )
    return None


def _canonical_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    return value


class CanonicalRequest(BaseModel):
    """Base class for every request body: text is stored in its canonical form.

    Put it **first** in the bases (`class X(CanonicalRequest, SomethingBase)`) so
    the validator runs before the model's own field validation.
    """

    @model_validator(mode="before")
    @classmethod
    def _canonicalise(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        fields = cls.model_fields
        canonicalised: dict[str, Any] = {}
        for key, value in data.items():
            field = fields.get(key)
            if field is None or _keeps_case(key) or _is_fixed_choice(field.annotation):
                canonicalised[key] = value
            elif _is_phone_field(key):
                # A phone number is stored as its ten digits (`canonical_phone`),
                # so "+91 98765 43210" and "98765 43210" cannot become two values.
                canonicalised[key] = (
                    canonical_phone(value) if isinstance(value, str) else value
                )
            else:
                canonicalised[key] = _canonical_value(value)
        return canonicalised
