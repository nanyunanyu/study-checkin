from typing import Optional

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class PasswordIn(BaseModel):
    oldPassword: str
    newPassword: str = Field(min_length=8, max_length=128)


class PlanItemIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    startTime: str = ""
    endTime: str = ""
    title: str = Field(min_length=1, max_length=200)
    subject: str = "其他"
    focusMin: Optional[int] = None
    note: str = ""
    active: bool = True


class PlanIn(BaseModel):
    items: list[PlanItemIn]


class TaskIn(BaseModel):
    id: str
    startTime: str = ""
    endTime: str = ""
    title: str = ""
    subject: str = "其他"
    note: str = ""
    done: bool = False
    focusSec: int = 0


class DayIn(BaseModel):
    tasks: list[TaskIn] = []
    review: dict = {}
    focusSec: int = 0
    checkedIn: bool = False


class UserCreateIn(BaseModel):
    username: str = Field(min_length=4, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    displayName: Optional[str] = None
    mustChangePassword: bool = False


class UserPatchIn(BaseModel):
    displayName: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None


class ResetPasswordIn(BaseModel):
    newPassword: str = Field(min_length=8, max_length=128)
    mustChangePassword: bool = False
