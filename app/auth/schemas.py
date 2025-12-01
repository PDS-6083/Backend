from enum import Enum

from pydantic import BaseModel, EmailStr


class UserType(str, Enum):
    ADMIN = "admin"
    CREW = "crew"
    SCHEDULER = "scheduler"
    ENGINEER = "engineer"


class LoginRequest(BaseModel):
    user_type: UserType
    email: EmailStr
    password: str


class UserInfo(BaseModel):
    id: str
    email: EmailStr
    user_type: UserType
    name: str | None = None


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: UserInfo | None = None
    token: str | None = None


class LogoutResponse(BaseModel):
    success: bool
    message: str


