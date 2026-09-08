import enum

from sqlmodel import Field, SQLModel


class RoleEnum(enum.StrEnum):
    director = "director"
    admin = "admin"
    principal = "principal"
    hod = "hod"
    class_teacher = "class_teacher"
    subject_teacher = "subject_teacher"
    teacher = "teacher"
    student = "student"
    guardian = "guardian"
    accountant = "accountant"
    librarian = "librarian"
    transport = "transport"
    staff = "staff"


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
