"""A fee head is filed against the **class catalog**, not against a class-section.

The New Fee Head modal posts a class name ("Class 1"); the service used to hand
`classroom_id=` to a schema whose field is `class_id`, so `POST
/finance/fee-structures` could never write a row. This pins the wiring: the head
lands on `classname.class_id` and starts as a Draft.
"""

from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.schema import load_models
from app.domains.academic.classroom.academics.models import ClassName
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.operations.fees_structure import service
from app.domains.operations.fees_structure.models import FeeStructure
from app.domains.operations.fees_structure.schemas import FeeStructureRowCreate


def memory_session() -> Session:
    """A throw-away in-memory database with the whole schema on it."""
    load_models()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_a_fee_head_is_filed_against_the_class_catalog() -> None:
    session = memory_session()
    school = School(name="fee school", code="fee", email="fee@test")
    catalog = ClassName(classname="Class 1", level=1, stage="primary")
    session.add(school)
    session.add(catalog)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    row = service.create_fee_structure_row(
        session,
        FeeStructureRowCreate(
            head="Tuition Fee",
            class_name="Class 1",
            frequency="Monthly",
            amount=1200,
        ),
    )

    stored = session.get(FeeStructure, row.id)
    assert stored is not None
    assert stored.class_id == catalog.class_id
    assert stored.status == "Draft"
    assert stored.name.lower() == "tuition fee"
    assert row.class_name == "Class 1"
    assert row.frequency == "Monthly"
    assert row.students == 0


def test_fee_heads_are_listed_for_their_academic_year_only() -> None:
    session = memory_session()
    school = School(name="fee year school", code="fey", email="fey@test")
    catalog = ClassName(classname="Class 1", level=1, stage="primary")
    first_year = AcademicYear(
        name="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
        school_id=school.id,
    )
    second_year = AcademicYear(
        name="2027-28",
        start_date=date(2027, 4, 1),
        end_date=date(2028, 3, 31),
        is_current=False,
        school_id=school.id,
    )
    session.add(school)
    session.add(catalog)
    session.add(first_year)
    session.add(second_year)
    session.commit()
    session.info["school_id"] = school.id

    first = service.create_fee_structure_row(
        session,
        FeeStructureRowCreate(
            head="Tuition Fee",
            class_name="Class 1",
            frequency="Monthly",
            amount=1200,
        ),
    )
    assert session.get(FeeStructure, first.id).academic_year_id == first_year.id

    first_year.is_current = False
    session.add(first_year)
    session.commit()
    second_year.is_current = True
    session.add(second_year)
    session.commit()
    assert service.list_fee_structure_rows(session) == []

    second = service.create_fee_structure_row(
        session,
        FeeStructureRowCreate(
            head="Tuition Fee",
            class_name="Class 1",
            frequency="Monthly",
            amount=1400,
        ),
    )
    assert session.get(FeeStructure, second.id).academic_year_id == second_year.id
    assert [row.id for row in service.list_fee_structure_rows(session)] == [second.id]
    assert [
        row.id for row in service.list_fee_structure_rows(session, first_year.id)
    ] == [first.id]
