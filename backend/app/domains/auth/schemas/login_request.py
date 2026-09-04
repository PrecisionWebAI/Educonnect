from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str | None = None
    identifier: str | None = None
    password: str
