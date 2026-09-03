# Schemas are already defined in users/models.py (UserCreate, UserRead)
# So we can just re-export or use them directly.
# This file is intentionally left mostly empty or can be used for extra schemas like Update.

from pydantic import BaseModel

from .models import RoleEnum


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    role: RoleEnum | None = None
    is_active: bool | None = None
