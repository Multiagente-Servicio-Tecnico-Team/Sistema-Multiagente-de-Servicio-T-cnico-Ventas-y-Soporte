"""Reglas de registro e inicio de sesión sobre la tabla users."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.schemas import RegistroIn, UsuarioOut
from app.accounts.security import hash_password, verify_password


class EmailAlreadyRegistered(Exception):
    pass


def to_out(user: User) -> UsuarioOut:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return UsuarioOut(id=user.id, nombre=user.name, apellido=user.last_name, email=user.email, rol=role)


def find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def register_user(db: Session, data: RegistroIn, rounds: int) -> User:
    """Crea un cliente. El rol queda en CUSTOMER por el valor por defecto de la tabla."""
    if find_by_email(db, data.email):
        raise EmailAlreadyRegistered()
    user = User(
        email=data.email,
        phone=data.telefono,
        password_hash=hash_password(data.password, rounds),
        name=data.nombre,
        last_name=data.apellido,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        # Dos registros simultáneos con el mismo correo: lo resuelve la restricción UNIQUE.
        db.rollback()
        raise EmailAlreadyRegistered() from exc
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str, fallback_hash: str) -> User | None:
    """Devuelve el usuario activo si la contraseña coincide. Siempre ejecuta una verificación bcrypt."""
    user = find_by_email(db, email)
    if user is None:
        verify_password(password, fallback_hash)
        return None
    if not verify_password(password, user.password_hash) or not user.active:
        return None
    return user
