"""Pruebas de la API de cuentas con SQLite en memoria; no requieren PostgreSQL."""
import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.accounts.api import create_app
from app.accounts.config import Settings
from app.accounts.models import Base, Role, User
from app.accounts.security import hash_password, sign_session

PASSWORD = "TriageTech#2026"
VALID = {"nombre": "Martín Gómez", "email": "Martin.Gomez@Gmail.com", "telefono": "+51 987 654 321", "password": PASSWORD}


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = Settings(database_url=None, auth_secret="s" * 48, secure_cookie=False, bcrypt_rounds=4)
    client = TestClient(create_app(settings, factory))
    return client, factory


def rows(factory):
    with factory() as db:
        return db.scalars(select(User)).all()


def add_user(factory, email, role=Role.CUSTOMER, active=True):
    with factory() as db:
        db.add(User(email=email, phone="+51911111111", password_hash=hash_password(PASSWORD, 4), name="Ana", last_name="Ruiz", role=role, active=active))
        db.commit()


# ---------- POST /registro ----------

def test_registro_crea_cliente_con_hash_bcrypt(env):
    client, factory = env
    res = client.post("/registro", json=VALID)

    assert res.status_code == 201
    assert res.json() == {"usuario": {"id": 1, "nombre": "Martín", "apellido": "Gómez", "email": "martin.gomez@gmail.com", "rol": "CUSTOMER"}}
    assert PASSWORD not in res.text and "$2b$" not in res.text

    [user] = rows(factory)
    assert user.email == "martin.gomez@gmail.com"
    assert user.phone == "+51987654321"
    assert (user.name, user.last_name, user.role, user.active) == ("Martín", "Gómez", Role.CUSTOMER, True)
    assert user.password_hash.startswith("$2b$") and user.password_hash != PASSWORD
    assert bcrypt.checkpw(PASSWORD.encode(), user.password_hash.encode())


def test_registro_acepta_apellido_separado(env):
    client, _ = env
    res = client.post("/registro", json={**VALID, "nombre": "María José", "apellido": "Pérez Díaz"})
    assert res.json()["usuario"]["nombre"] == "María José"
    assert res.json()["usuario"]["apellido"] == "Pérez Díaz"


def test_registro_ignora_rol_enviado_por_el_cliente(env):
    client, factory = env
    client.post("/registro", json={**VALID, "rol": "ADMIN", "role": "ADMIN"})
    assert rows(factory)[0].role == Role.CUSTOMER


def test_registro_rechaza_correo_duplicado_sin_crear_filas(env):
    client, factory = env
    assert client.post("/registro", json=VALID).status_code == 201
    res = client.post("/registro", json={**VALID, "email": "MARTIN.GOMEZ@gmail.com"})

    assert res.status_code == 409
    assert res.json() == {"detail": "El correo ya está registrado.", "field": "email"}
    assert len(rows(factory)) == 1


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"email": "no-es-correo"}, "email"),
        ({"telefono": "987654321"}, "telefono"),
        ({"password": "Corta#1"}, "password"),
        ({"password": "sinmayuscula#2026"}, "password"),
        ({"password": "SinSimbolo2026"}, "password"),
        ({"password": "Aa#1" + "x" * 80}, "password"),
        ({"nombre": "Al"}, "nombre"),
    ],
)
def test_registro_valida_datos_sin_devolver_la_contrasena(env, patch, field):
    client, factory = env
    res = client.post("/registro", json={**VALID, **patch})

    assert res.status_code == 422
    assert res.json()["field"] == field
    assert patch.get("password", PASSWORD) not in res.text
    assert rows(factory) == []


def test_registro_sin_campos_obligatorios(env):
    client, _ = env
    res = client.post("/registro", json={"email": "a@b.pe"})
    assert res.status_code == 422
    assert {e["campo"] for e in res.json()["errors"]} >= {"nombre", "telefono", "password"}


# ---------- POST /login, /me, /logout ----------

def test_login_correcto_abre_sesion_con_cookie_segura(env):
    client, _ = env
    client.post("/registro", json=VALID)
    res = client.post("/login", json={"email": "  MARTIN.gomez@gmail.com ", "password": PASSWORD})

    assert res.status_code == 200
    assert res.json()["usuario"]["email"] == "martin.gomez@gmail.com"
    cookie = res.headers["set-cookie"]
    assert cookie.startswith("techfix_session=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=28800" in cookie
    assert client.get("/me").json()["usuario"]["nombre"] == "Martín"


def test_login_fallido_usa_el_mismo_mensaje(env):
    client, _ = env
    client.post("/registro", json=VALID)
    wrong = client.post("/login", json={"email": VALID["email"], "password": "Otra#Clave2026"})
    unknown = client.post("/login", json={"email": "nadie@techfix.ai", "password": PASSWORD})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Correo o contraseña incorrectos."}
    assert "set-cookie" not in wrong.headers


def test_cuenta_inactiva_no_inicia_sesion(env):
    client, factory = env
    add_user(factory, "inactiva@techfix.ai", active=False)
    assert client.post("/login", json={"email": "inactiva@techfix.ai", "password": PASSWORD}).status_code == 401


def test_login_devuelve_rol_del_personal(env):
    client, factory = env
    add_user(factory, "tecnico@taller.com", role=Role.TECHNICIAN)
    res = client.post("/login", json={"email": "tecnico@taller.com", "password": PASSWORD})
    assert res.json()["usuario"]["rol"] == "TECHNICIAN"


def test_contrasena_mayor_a_72_bytes_no_rompe_el_login(env):
    client, _ = env
    client.post("/registro", json=VALID)
    assert client.post("/login", json={"email": VALID["email"], "password": "A#1" + "ñ" * 200}).status_code == 401


def test_bloquea_tras_cinco_intentos_fallidos(env):
    client, _ = env
    client.post("/registro", json=VALID)
    for _ in range(5):
        assert client.post("/login", json={"email": VALID["email"], "password": "Mala#2026"}).status_code == 401
    blocked = client.post("/login", json={"email": VALID["email"], "password": PASSWORD})
    assert blocked.status_code == 429


def test_me_sin_cookie_o_alterada_responde_401(env):
    client, _ = env
    assert client.get("/me").status_code == 401
    client.cookies.set("techfix_session", sign_session(1, "otro-secreto" * 4, 3600))
    assert client.get("/me").status_code == 401


def test_logout_borra_la_sesion(env):
    client, _ = env
    client.post("/registro", json=VALID)
    client.post("/login", json={"email": VALID["email"], "password": PASSWORD})
    assert client.post("/logout").status_code == 204
    assert client.get("/me").status_code == 401


# ---------- CORS y salud ----------

def test_cors_solo_para_el_frontend_configurado(env):
    client, _ = env
    headers = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    ok = client.options("/login", headers={**headers, "Origin": "http://localhost:5173"})
    other = client.options("/login", headers={**headers, "Origin": "http://evil.example"})

    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert ok.headers["access-control-allow-credentials"] == "true"
    assert "access-control-allow-origin" not in other.headers


def test_salud(env):
    client, _ = env
    assert client.get("/salud").json() == {"estado": "ok", "bd": "ok"}


def test_registro_concurrente_respeta_unicidad(env):
    """Si dos registros pasan la verificación previa, la restricción UNIQUE devuelve 409."""
    _, factory = env
    from app.accounts.schemas import RegistroIn
    from app.accounts.service import EmailAlreadyRegistered, register_user

    data = RegistroIn(**VALID)
    with factory() as db:
        register_user(db, data, 4)
    with factory() as db, pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.accounts.service.find_by_email", lambda *_: None)
        with pytest.raises(EmailAlreadyRegistered):
            register_user(db, data, 4)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
