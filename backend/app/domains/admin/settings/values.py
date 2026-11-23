"""The school's own policy numbers - `school_setting`, read with a default.

The three readers here exist so no screen hardcodes a policy again:

* `get_value`  - the stored text, or the default from `DEFAULTS`;
* `get_int`    - the same for a numeric policy (`75`), ignoring a stored row that is
  not a number;
* `set_value`  - write one answer for this school (one row per key).

The defaults are the **starting point**, not the truth: a school that wants 80% sets
`attendance.absence_threshold = 80` once and every screen (register summary, attention
list, Phase 4's threshold chip) follows, because they all come through here.
"""

from sqlmodel import Session, select

from app.core.tenancy import tenant_of

from .models import SchoolSetting

#: What a school gets before it sets anything. Keys are dotted and stable.
DEFAULTS: dict[str, str] = {
    #: Below this attendance percentage a child is "below threshold".
    "attendance.absence_threshold": "75",
    #: This many absences in a row is a pattern worth calling the family about.
    "attendance.consecutive_days": "3",
    #: Late days, as a share of a month's open days, that put a child on the late list.
    "attendance.late_share_percent": "10",
    #: The weekdays the school is regularly closed, `date.weekday()` order
    #: (0 = Monday .. 6 = Sunday), comma separated: "6" is Sunday only, "5,6" is
    #: Saturday and Sunday. One setting for every week - never a row per Sunday.
    #: A `#` token narrows it to some weeks of the month: "5#1" is the **1st Saturday**
    #: only, so "6,5#1,5#3" reads "every Sunday, plus the 1st and 3rd Saturday".
    "attendance.weekly_off_days": "6",
    #: When the exam reminder goes out (Phase 7 reads it).
    "exam.reminder_time": "18:00",
    #: `section` / `class` / `school` - how wide a rank is printed (Phase 7).
    "exam.rank_display": "section",
    #: `percentage` / `grade` - which scale the report card prints (Phase 7).
    "exam.grade_scale": "percentage",
}


def get_value(session: Session, key: str, default: str | None = None) -> str | None:
    """This school's answer for `key`, else the built-in default, else `default`."""
    row = session.exec(select(SchoolSetting).where(SchoolSetting.key == key)).first()
    if row is not None and row.value is not None:
        return row.value
    if key in DEFAULTS:
        return DEFAULTS[key]
    return default


def get_int(session: Session, key: str, default: int) -> int:
    """`get_value` for a numeric policy - a stored non-number falls back, never raises."""
    raw = get_value(session, key)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except TypeError, ValueError:
        return default


def set_value(session: Session, key: str, value: str | int) -> SchoolSetting:
    """Write one answer for this school (one row per key - updated, never duplicated)."""
    text = str(value)
    row = session.exec(select(SchoolSetting).where(SchoolSetting.key == key)).first()
    if row is None:
        row = SchoolSetting(key=key, value=text, school_id=tenant_of(session))
    else:
        row.value = text
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
