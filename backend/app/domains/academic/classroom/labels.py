"""The class-section label every screen prints - one implementation.

A class-section is a `classroom` row: the class name comes from `classname`, the
letter from `section`, and screens print the two as "Class 10-A". That string is
built in a dozen places, so it lives here instead of being re-typed (and drifting)
in each service.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import ClassName, Classroom, Section


def label(class_name: str | None, section_name: str | None) -> str:
    """`Class 10-A` from the two catalog words; `""` when there is no class."""
    if not class_name:
        return section_name or ""
    return f"{class_name}-{section_name}" if section_name else class_name


def labels_by_section(
    session: Session, section_ids: list[UUID]
) -> dict[UUID, str]:
    """{classroom_id: label} for many class-sections, in two queries.

    The screens that list the whole school print one label per row; reading the
    class and the letter per row is what made those lists slow, so both catalogs
    are read once and joined in memory.
    """
    wanted = [section_id for section_id in dict.fromkeys(section_ids) if section_id]
    if not wanted:
        return {}

    rooms = {
        room.id: room
        for room in session.exec(
            select(Classroom).where(Classroom.id.in_(wanted))
        ).all()
    }
    class_ids = [room.class_id for room in rooms.values() if room.class_id]
    section_letters = [room.section_id for room in rooms.values() if room.section_id]
    classes = (
        {
            item.class_id: item
            for item in session.exec(
                select(ClassName).where(ClassName.class_id.in_(class_ids))
            ).all()
        }
        if class_ids
        else {}
    )
    letters = (
        {
            item.section_id: item
            for item in session.exec(
                select(Section).where(Section.section_id.in_(section_letters))
            ).all()
        }
        if section_letters
        else {}
    )

    found: dict[UUID, str] = {}
    for room_id, room in rooms.items():
        classroom = classes.get(room.class_id) if room.class_id else None
        letter = letters.get(room.section_id) if room.section_id else None
        found[room_id] = label(
            classroom.classname if classroom else None,
            letter.section_name if letter else None,
        )
    return found
