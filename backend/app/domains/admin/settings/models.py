"""The Settings screen's own rows: the security log and the gateway statuses.

Both are read-only lists the school keeps for itself; the users table and the
school's own details are read from the real `user` / `school` tables instead
(see `service.py`), so there is nothing to duplicate here.
"""

from sqlmodel import SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class SecurityLogBase(SQLModel):
    event: str
    user: str  # the login/email as shown on the screen
    when: str  # "Today, 09:12"


class SecurityLog(SecurityLogBase, TenantMixin, UUIDMixin, table=True):
    pass


class GatewayStatusBase(SQLModel):
    name: str
    type: str
    status: str
    quota: str


class GatewayStatus(GatewayStatusBase, TenantMixin, UUIDMixin, table=True):
    pass
