import re

from pydantic import BaseModel, Field, field_validator


class CredentialsDto(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value


class UserDto(BaseModel):
    id: int
    email: str
    created_at: str


class AuthResponseDto(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserDto
