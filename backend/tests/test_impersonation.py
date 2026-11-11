"""The "switch account" token must be encode-able, and readable back.

`POST /auth/impersonate` used to answer 500 with

    TypeError: Object of type UUID is not JSON serializable

because the `act` (admin) and `imp` (audit row) claims were passed to
`jwt.encode` as raw UUIDs while `sub` was converted. The UI could only report
"Could not switch account". These tests pin the contract: any id may be handed to
`create_access_token`, and the claims come back as the same text.

The same holds for the `sch` claim of "switch school" - the administrator's own
token, pinned to one school (`school_scope_from_token`). A missing, unreadable or
non-UUID claim has to read as "no scope", because that is the platform-wide view
an ordinary login has.
"""

from uuid import UUID, uuid4

import jwt

from app.core.config import settings
from app.core.security import (
    actor_id_from_token,
    create_access_token,
    school_scope_from_token,
)


def decode(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


def test_impersonation_claims_accept_raw_uuids():
    actor, target, log = uuid4(), uuid4(), uuid4()

    token = create_access_token(subject=target, extra_claims={"act": actor, "imp": log})
    payload = decode(token)

    assert payload["sub"] == str(target)
    assert payload["act"] == str(actor)
    assert payload["imp"] == str(log)


def test_actor_id_reads_back_as_a_uuid():
    actor = uuid4()
    token = create_access_token(subject=uuid4(), extra_claims={"act": actor})

    found = actor_id_from_token(token)

    assert isinstance(found, UUID)
    assert found == actor


def test_a_normal_token_has_no_actor():
    """A plain login is not an impersonated session."""
    assert actor_id_from_token(create_access_token(subject=uuid4())) is None


def test_an_unreadable_token_has_no_actor():
    """`stop` treats this as "not impersonating" instead of blowing up."""
    assert actor_id_from_token("not-a-token") is None


def test_a_school_scope_reads_back_as_a_uuid():
    """`sch` travels as text and comes back as the school id, like `act` does."""
    school = uuid4()

    token = create_access_token(subject=uuid4(), extra_claims={"sch": school})

    assert decode(token)["sch"] == str(school)
    assert school_scope_from_token(token) == school


def test_a_plain_token_has_no_school_scope():
    """A normal login is the platform-wide view, not a scoped one."""
    assert school_scope_from_token(create_access_token(subject=uuid4())) is None


def test_clearing_a_scope_leaves_no_claim():
    """`POST /auth/scope/school {school_id: null}` mints a token with no `sch`."""
    token = create_access_token(subject=uuid4(), extra_claims=None)

    assert "sch" not in decode(token)
    assert school_scope_from_token(token) is None


def test_an_unreadable_token_has_no_school_scope():
    """A garbage claim is "no scope", not a crash: the binding still has to work."""
    assert school_scope_from_token("not-a-token") is None
    assert school_scope_from_token(None) is None


def test_a_claim_that_is_not_a_uuid_is_ignored():
    token = create_access_token(subject=uuid4(), extra_claims={"sch": "somewhere"})

    assert school_scope_from_token(token) is None


def test_claim_values_that_are_already_json_survive_untouched():
    token = create_access_token(
        subject="user-1",
        extra_claims={"act": "abc", "n": 7, "flag": True, "missing": None},
    )
    payload = decode(token)

    assert payload["act"] == "abc"
    assert payload["n"] == 7
    assert payload["flag"] is True
    assert payload["missing"] is None
