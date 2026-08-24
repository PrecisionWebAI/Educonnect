import enum

from sqlmodel import Field, SQLModel


class RoleEnum(enum.StrEnum):
    director = "director"
    principal = "principal"
    hod = "hod"
    # Class teacher / Subject teacher can be sub-roles or just teacher
    teacher = "teacher"
    student = "student"
    parent = "parent"
    accountant = "accountant"
    admin = "admin"


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: str
    role: RoleEnum
    is_active: bool = True


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
