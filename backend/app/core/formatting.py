"""The two date formats the screens print - one implementation.

Rows store `date` / `datetime`; the tables print `2026/11/11` and
`2026/11/11 09:12`. Leave, library, tickets and meetings show the same columns, so
the format lives here instead of being re-typed in every feature. A row with no
value prints an empty cell rather than "None".
"""

from datetime import date, datetime


def day(value: date | None) -> str:
    """`2026/11/11` for a date; "" when the row has none."""
    return value.strftime("%Y/%m/%d") if value else ""


def stamp(value: datetime | None) -> str:
    """`2026/11/11 09:12` for a timestamp; "" when the row has none."""
    return value.strftime("%Y/%m/%d %H:%M") if value else ""
