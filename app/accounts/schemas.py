"""Cuerpos de petición y respuesta. Las reglas repiten las del formulario del frontend."""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

# Mismo patrón que la restricción chk_email_format del script de BD.
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+\d{8,15}$")


def check_password_policy(value: str) -> str:
    """Política común de registro y restablecimiento: 8 a 72 bytes, mayúscula, número y símbolo."""
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


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nombre: str = Field(max_length=200)
    apellido: str | None = Field(default=None, max_length=100)
    email: str
    telefono: str
    password: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("telefono")
    @classmethod
    def telefono_valido(cls, value: str) -> str:
        phone = re.sub(r"[\s-]", "", value)
        if not PHONE_RE.match(phone):
            raise ValueError("Ingresa el teléfono con código de país, por ejemplo +51987654321.")
        return phone

    @field_validator("password")
    @classmethod
    def password_segura(cls, value: str) -> str:
        return check_password_policy(value)

    @model_validator(mode="after")
    def separar_nombre(self) -> "RegistroIn":
        nombre = " ".join(self.nombre.split())
        apellido = " ".join(self.apellido.split()) if self.apellido else None
        if apellido is None and " " in nombre:
            # El formulario de Figma tiene un solo campo "Nombre y Apellido".
            nombre, apellido = nombre.split(" ", 1)
        # El tipo "nombre" permite a la API indicar el campo aunque el error sea del modelo completo.
        if len(f"{nombre} {apellido or ''}".strip()) < 3 or not nombre:
            raise PydanticCustomError("nombre", "Ingresa tu nombre y apellido.")
        if len(nombre) > 100 or (apellido and len(apellido) > 100):
            raise PydanticCustomError("nombre", "El nombre y el apellido admiten hasta 100 caracteres cada uno.")
        self.nombre, self.apellido = nombre, apellido or None
        return self


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def email_normalizado(cls, value: str) -> str:
        return value.strip().lower()


class RecuperarIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, value: str) -> str:
        return _normalize_email(value)


class RestablecerIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    token: str = Field(min_length=16, max_length=256)
    password: str

    @field_validator("password")
    @classmethod
    def password_segura(cls, value: str) -> str:
        return check_password_policy(value)


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    apellido: str | None
    email: str
    rol: str


class UsuarioRespuesta(BaseModel):
    usuario: UsuarioOut
