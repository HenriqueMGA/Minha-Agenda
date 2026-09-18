from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    email: str
    type: str


class UserUpdate(BaseModel):
    name: str | None = None
    username: str | None = None
    password: str | None = None
    type: str | None = None
    email: str | None = None


class UserResponse(BaseModel):
    email: str
    username: str
