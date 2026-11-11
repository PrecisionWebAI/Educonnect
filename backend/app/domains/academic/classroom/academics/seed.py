"""The class catalog - an app-level seeder, like the role catalog.

Same shape as the other catalog seeders (`permissions_repository.seed_roles`,
`seed_permissions`): it takes a `Session`, does its inserts, prints what it did and
returns. `app/core/bootstrap.py` is what opens the session.

`classroom` and `section` carry a `school_id`, so the catalog is seeded **per
active school**: every school gets its own 15 classes and 150 sections, and
`app/core/db.py` keeps one school's classes out of another's queries. `role` and
`permission` are the opposite - platform catalogs, seeded once.

The seeder runs on an unbound session (no school), so the tenant listener neither
filters the reads nor stamps the inserts; every `school_id` here is set explicitly.

Idempotent: every step looks for what it is about to insert, so it is safe on
every container start.
"""



from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import ClassName, Section, Subject
from app.domains.admin.platform.models import School

#: (name, level, stage). `level` is the position inside the school (0 = Nursery),
#: not the class number: the pre-primary years have no number and a school may
#: call a year "Std VI". The name is the truth; the level only sorts.
#:
#: Names are stored the way `app/core/text.py` stores every value - lower-case -
#: and the frontend renders them in Title Case ("class 6" → "Class 6"). Writing
#: them here in Title Case would put two spellings of one class in the catalog.
CLASS_CATALOG: tuple[tuple[str, int, str], ...] = (
    ("nursery", 0, "pre_primary"),
    ("lkg", 1, "pre_primary"),
    ("ukg", 2, "pre_primary"),
    ("class 1", 3, "primary"),
    ("class 2", 4, "primary"),
    ("class 3", 5, "primary"),
    ("class 4", 6, "primary"),
    ("class 5", 7, "primary"),
    ("class 6", 8, "middle"),
    ("class 7", 9, "middle"),
    ("class 8", 10, "middle"),
    ("class 9", 11, "secondary"),
    ("class 10", 12, "secondary"),
    ("class 11", 13, "senior_secondary"),
    ("class 12", 14, "senior_secondary"),
)

#: Every class runs the same ten sections (lower-case, like every stored value).
SECTION_NAMES: tuple[str, ...] = tuple("abcdefghij")

#: Default subjects seeded per active school (tenant-scoped, like `classroom` is
#: shared - but subjects carry a `school_id` so each school can rename/add them).
#: The name is canonical text (lower-case); the code is an identifier and keeps
#: the case it is written in.
SUBJECT_CATALOG: tuple[tuple[str, str], ...] = (
    ("mathematics", "MATH"),
    ("english", "ENG"),
    ("hindi", "HIN"),
    ("physics", "PHY"),
    ("chemistry", "CHEM"),
    ("biology", "BIO"),
    ("computer science", "CS"),
    ("social science", "SST"),
    ("history", "HIS"),
    ("geography", "GEO"),
    ("physical education", "PE"),
    ("art", "ART"),
    ("music", "MUS"),
)



def _sync_catalogs(session: Session) -> tuple[int, int]:
    """The two **platform** catalogs: the 15 classes and the A-J sections.

    Neither table carries a `school_id`, so this is not per school: every school
    reads the same 15 classes and the same 10 sections, and a class id means the
    same thing everywhere. It is idempotent, so it runs on every start and only
    fills what is missing.

    A school's own class-sections are **not** seeded here. A `classroom` row
    ("Class 10-A") is written the moment the school uses it - a student is
    registered into it, a class teacher is assigned, or a period is added.
    """
    created_classes = 0
    for name, level, stage in CLASS_CATALOG:
        found = session.exec(
            select(ClassName).where(func.lower(ClassName.classname) == name.lower())
        ).first()
        if found is None:
            session.add(ClassName(classname=name, level=level, stage=stage))
            created_classes += 1
            continue
        # Keep level/stage truthful even on rows written before they existed.
        if found.level != level or found.stage != stage:
            found.level = level
            found.stage = stage
            session.add(found)

    created_sections = 0
    for section_name in SECTION_NAMES:
        found = session.exec(
            select(Section).where(
                func.upper(Section.section_name) == section_name.upper()
            )
        ).first()
        if found is None:
            session.add(Section(section_name=section_name))
            created_sections += 1
    session.commit()

    if created_classes or created_sections:
        print(
            f"[academics] platform catalog: {created_classes} class(es), "
            f"{created_sections} section(s) created"
        )
    return created_classes, created_sections


def _sync_subjects(session: Session) -> int:
    """Give every active school the default subject list (idempotent)."""
    schools = session.exec(select(School).where(School.is_active == True)).all()
    created = 0
    for school in schools:
        present = {
            subject.name: subject
            for subject in session.exec(
                select(Subject).where(Subject.school_id == school.id)
            ).all()
        }
        for name, code in SUBJECT_CATALOG:
            if name in present:
                continue
            session.add(Subject(name=name, code=code, school_id=school.id))
            created += 1
    session.commit()
    if created:
        print(f"[academics] {created} subject(s) created")
    return created


def seed_academics(session: Session) -> tuple[int, int]:
    """Seed the platform's class/section catalogs. Returns (classes, sections).

    The two catalogs are **platform-wide** (no `school_id`): one set of 15 classes
    and one set of A-J, shared by every school. A school's own class-sections are
    created as it uses them, never here.

    `subject` is the opposite - it carries a `school_id`, so every active school
    gets its own copy and can rename or add to it.
    """
    classes, sections = _sync_catalogs(session)
    subjects = _sync_subjects(session)
    print(
        f"[academics] class/section catalog ready: {classes} class(es), "
        f"{sections} section(s) added, {subjects} subject(s) created"
    )
    return (classes, sections)
