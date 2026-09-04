from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums import RoleName


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    totp_code: str | None = Field(default=None, max_length=12)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    requires_2fa: bool = False
    role: str = ""
    username: str = ""


class UserOut(ORMModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    totp_enabled: bool
    last_login_at: datetime | None
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    full_name: str = Field(default="", max_length=255)
    password: str = Field(min_length=10, max_length=128)
    role: RoleName


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=255)
    role: RoleName | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class TwoFASetupOut(BaseModel):
    secret: str
    otpauth_url: str


class TwoFAConfirm(BaseModel):
    code: str = Field(min_length=6, max_length=12)
