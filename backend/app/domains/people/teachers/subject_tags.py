"""A teacher's subjects, as plain informational text.

`employee.subject_tags` is a comma-separated line ("English, Maths") - what the hire form
collects and the profile drawer shows. It says what a person *can* teach; it never
decides who *may* teach: any active teacher can be given any section subject, and the
tags only help a human (and the cover board's ranking) choose.

One function owns the shape, so the hire form, the profile drawer and the rehire path
cannot store the same words differently.
"""

from fastapi import HTTPException

MAX_LENGTH = 500


def split_tags(value: str | None) -> list[str]:
    """The tags in a stored line, in order, blanks gone."""
    return [" ".join(part.split()) for part in (value or "").split(",") if part.strip()]


def normalise(value: str | None) -> str | None:
    """Trim every tag, collapse inner spaces, drop repeats (any case), join with ", ".

    Returns `None` for "no tags" so an empty form clears the column instead of storing
    an empty string; a line longer than the column is a `422`, never a silent cut.
    """
    seen: set[str] = set()
    tags: list[str] = []
    for part in (value or "").split(","):
        tag = " ".join(part.split())
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    line = ", ".join(tags)
    if len(line) > MAX_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Subjects can be at most {MAX_LENGTH} characters in all.",
        )
    return line or None


def mentions(value: str | None, subject_name: str) -> bool:
    """True when a tag line lists `subject_name` (case-insensitive, whole tag)."""
    wanted = " ".join((subject_name or "").split()).lower()
    return bool(wanted) and any(tag.lower() == wanted for tag in split_tags(value))
