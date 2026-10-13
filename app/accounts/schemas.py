"""Request and response bodies. The rules mirror the frontend form.

Python attributes are in English; the JSON keys of the public contract stay in Spanish through aliases
(nombre, apellido, telefono, usuario, rol), so the frontend, Postman and the pattern APIs keep working.
"""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

# Same pattern as the chk_email_format constraint in the database script.
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+\d{8,15}$")
# Error type that lets the API report the "nombre" field when the error belongs to the whole model.
FULL_NAME_ERROR = "full_name"


def check_password_policy(value: str) -> str:
    """Shared rule for sign-up and reset: 8 to 72 bytes, an uppercase letter, a digit and a symbol."""
    size = len(value.encode("utf-8"))
    checks = [
        8 <= size <= 72,
        re.search(r"[A-Z]", value),
        re.search(r"\d", value),
        re.search(r"[^A-Za-z0-9]", value),
    ]
    if not all(checks):
        raise ValueError("La contraseña debe tener entre 8 y 72 caracteres, una mayúscula, un número y un símbolo.")
    return value


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 255 or not EMAIL_RE.match(email):
        raise ValueError("Ingresa un correo electrónico válido.")
    return email


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_by_name=True, validate_by_alias=True)

    first_name: str = Field(alias="nombre", max_length=200)
    last_name: str | None = Field(default=None, alias="apellido", max_length=100)
    email: str
    phone: str = Field(alias="telefono")
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        phone = re.sub(r"[\s-]", "", value)
        if not PHONE_RE.match(phone):
            raise ValueError("Ingresa el teléfono con código de país, por ejemplo +51987654321.")
        return phone

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return check_password_policy(value)

    @model_validator(mode="after")
    def split_full_name(self) -> "RegisterIn":
        first_name = " ".join(self.first_name.split())
        last_name = " ".join(self.last_name.split()) if self.last_name else None
        if last_name is None and " " in first_name:
            # The Figma form has a single "Nombre y Apellido" field.
            first_name, last_name = first_name.split(" ", 1)
        if len(f"{first_name} {last_name or ''}".strip()) < 3 or not first_name:
            raise PydanticCustomError(FULL_NAME_ERROR, "Ingresa tu nombre y apellido.")
        if len(first_name) > 100 or (last_name and len(last_name) > 100):
            raise PydanticCustomError(FULL_NAME_ERROR, "El nombre y el apellido admiten hasta 100 caracteres cada uno.")
        self.first_name, self.last_name = first_name, last_name or None
        return self


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class PasswordRecoveryIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class PasswordResetIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    token: str = Field(min_length=16, max_length=256)
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return check_password_policy(value)


class UserOut(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, serialize_by_alias=True)

    id: int
    first_name: str = Field(alias="nombre")
    last_name: str | None = Field(alias="apellido")
    email: str
    role: str = Field(alias="rol")


class UserResponse(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, serialize_by_alias=True)

    user: UserOut = Field(alias="usuario")
