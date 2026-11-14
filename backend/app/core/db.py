from sqlalchemy import event
from sqlalchemy.orm import with_loader_criteria
from sqlmodel import Session, create_engine

from app.core.config import settings
from app.core.tenancy import SKIP_SCHOOL, TenantError, TenantMixin, tenant_of

# `search_path` makes all unqualified tables resolve to the configured schema
# (`public` everywhere; kept configurable for a schema-per-tenant deployment).
_CONNECT_ARGS: dict[str, object] = {
    "options": f"-csearch_path={settings.DB_SCHEMA},public"
}
if settings.DB_SSLMODE:
    # Supabase (and every managed Postgres) terminates TLS with its own CA, so the
    # `sslmode` from the DSN is repeated for the driver's connection too.
    _CONNECT_ARGS["sslmode"] = settings.DB_SSLMODE

engine = create_engine(
    settings.DATABASE_URL,
    # A debugging switch, not a fixture: `SQL_ECHO=1` when you want the SQL.
    echo=settings.SQL_ECHO,
    # A pooled / managed database closes idle connections; a stale handle would
    # otherwise surface as a random "server closed the connection" on a request.
    pool_pre_ping=True,
    connect_args=_CONNECT_ARGS,
)


# ---------------------------------------------------------------------------
# Tenant enforcement (see app/core/tenancy.py for the reasoning)
# ---------------------------------------------------------------------------


def _tenant_models() -> list[type]:
    """Every mapped class that owns a `school_id`.

    `with_loader_criteria` has to be given a **mapped** entity: `TenantMixin`
    itself is a Pydantic model, so `TenantMixin.school_id` is a field rather than
    a class-level column and the criteria cannot be attached to it. Its direct
    subclasses are exactly the table classes, which is the list we need.

    Computed lazily and cached: `app.core.db` is imported *before* the model
    modules, so building this at import time would capture an empty list and the
    tenant filter would silently never apply. The cache is refreshed whenever the
    set of mapped subclasses changes (a new model module was imported) - compared
    by identity, not by count: one module added while another is removed would
    keep the same length and leave a stale, unfiltered list behind.
    """
    models = [
        model
        for model in TenantMixin.__subclasses__()
        if getattr(model, "__table__", None) is not None
    ]
    global _TENANT_MODELS
    if _TENANT_MODELS is None or set(_TENANT_MODELS) != set(models):
        _TENANT_MODELS = models
    return _TENANT_MODELS


_TENANT_MODELS: list[type] | None = None


@event.listens_for(Session, "do_orm_execute")
def _scope_selects_to_school(execute_state) -> None:
    """Add `WHERE school_id = <session school>` to every ORM SELECT.

    One listener covers every query in the app (`include_aliases=True` covers
    joins too), so a repository cannot forget the filter.
    """
    if not execute_state.is_select:
        return
    # Column/relationship loads are part of a statement that is already filtered;
    # adding criteria again would only duplicate the WHERE clause.
    if execute_state.is_column_load or execute_state.is_relationship_load:
        return
    if execute_state.execution_options.get(SKIP_SCHOOL, False):
        return

    school_id = tenant_of(execute_state.session)
    if school_id is None:
        # Platform role (or a seed / test): no school, no narrowing.
        return

    execute_state.statement = execute_state.statement.options(
        *(
            with_loader_criteria(
                model,
                lambda cls: cls.school_id == school_id,
                include_aliases=True,
            )
            for model in _tenant_models()
        )
    )


@event.listens_for(Session, "before_flush")
def _stamp_and_guard_school(session: Session, flush_context, instances) -> None:
    """Fill `school_id` on new rows, and refuse to write into another school."""
    school_id = tenant_of(session)
    if school_id is None:
        # Platform role: it may write anywhere, but it must say where.
        return

    for obj in session.new:
        if not isinstance(obj, TenantMixin):
            continue
        if obj.school_id is None:
            obj.school_id = school_id
        elif obj.school_id != school_id:
            raise TenantError(
                f"{type(obj).__name__} belongs to school {obj.school_id}, "
                f"but this request is scoped to school {school_id}"
            )

    for obj in session.dirty:
        if not isinstance(obj, TenantMixin):
            continue
        if obj.school_id is not None and obj.school_id != school_id:
            raise TenantError(
                f"{type(obj).__name__} belongs to school {obj.school_id}, "
                f"but this request is scoped to school {school_id}"
            )


def get_session():
    with Session(engine) as session:
        yield session
