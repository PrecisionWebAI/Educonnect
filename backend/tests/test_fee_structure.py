"""A fee head is filed against the **class catalog**, not against a class-section.

The New Fee Head modal posts a class name ("Class 1"); the service used to hand
`classroom_id=` to a schema whose field is `class_id`, so `POST
/finance/fee-structures` could never write a row. This pins the wiring: the head
lands on `classname.class_id` and starts as a Draft.
"""

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.schema import load_models
from app.domains.academic.classroom.academics.models import ClassName
from app.domains.operations.fees_structure import service
from app.domains.operations.fees_structure.models import FeeStructure
from app.domains.operations.fees_structure.schemas import FeeStructureRowCreate
from app.domains.admin.platform.models import School


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
