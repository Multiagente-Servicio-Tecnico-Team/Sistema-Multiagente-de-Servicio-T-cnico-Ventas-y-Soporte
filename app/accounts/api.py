"""API de cuentas: POST /registro, POST /login, POST /logout, GET /me y GET /salud.

Ejecutar:  uvicorn app.accounts.api:create_app --factory --host localhost --port 8000
"""
import logging

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.accounts.config import Settings
from app.accounts.models import User
from app.accounts.schemas import LoginIn, RegistroIn, UsuarioRespuesta
from app.accounts.security import LoginLimiter, dummy_hash, read_session, sign_session
from app.accounts.service import EmailAlreadyRegistered, authenticate, register_user, to_out

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "Correo o contraseña incorrectos."
TOO_MANY = "Demasiados intentos. Espera unos minutos antes de volver a intentar."


def _validation_response(exc: RequestValidationError) -> JSONResponse:
    """422 sin devolver los valores enviados (podrían incluir la contraseña)."""
    errors = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", ()) if part != "body"]
        message = str(err.get("msg", "Valor inválido.")).removeprefix("Value error, ")
        campo = loc[0] if loc else ("nombre" if err.get("type") == "nombre" else None)
        errors.append({"campo": campo, "mensaje": message})
    field = next((e["campo"] for e in errors if e["campo"]), None)
    return JSONResponse(status_code=422, content={"detail": "Datos inválidos.", "field": field, "errors": errors})


def create_app(settings: Settings | None = None, session_factory: sessionmaker | None = None) -> FastAPI:
    load_dotenv()
    settings = settings or Settings.from_env()
    if session_factory is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL no está configurada.")
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    app = FastAPI(title="TechFix.AI · Cuentas", version="1.0.0")
    app.state.settings = settings
    app.state.limiter = LoginLimiter(settings.max_failed_logins, settings.lockout_seconds)
    fallback_hash = dummy_hash(settings.bcrypt_rounds)
    max_age = settings.session_hours * 3600

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(_request: Request, exc: RequestValidationError):
        return _validation_response(exc)

    @app.exception_handler(OperationalError)
    async def on_db_unavailable(_request: Request, _exc: OperationalError):
        logger.error("Base de datos no disponible")
        return JSONResponse(status_code=503, content={"detail": "Servicio no disponible. Inténtalo más tarde."})

    def get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    def set_session_cookie(response: Response, user: User) -> None:
        response.set_cookie(
            settings.cookie_name,
            sign_session(user.id, settings.auth_secret, max_age),
            max_age=max_age,
            httponly=True,
            secure=settings.secure_cookie,
            samesite="lax",
            path="/",
        )

    @app.post("/registro", status_code=201, response_model=UsuarioRespuesta)
    def registro(body: RegistroIn, db: Session = Depends(get_db)):
        try:
            user = register_user(db, body, settings.bcrypt_rounds)
        except EmailAlreadyRegistered:
            return JSONResponse(status_code=409, content={"detail": "El correo ya está registrado.", "field": "email"})
        return {"usuario": to_out(user)}

    @app.post("/login", response_model=UsuarioRespuesta)
    def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
        limiter: LoginLimiter = app.state.limiter
        if limiter.blocked(body.email):
            return JSONResponse(status_code=429, content={"detail": TOO_MANY})
        user = authenticate(db, body.email, body.password, fallback_hash)
        if user is None:
            limiter.fail(body.email)
            return JSONResponse(status_code=401, content={"detail": INVALID_CREDENTIALS})
        limiter.reset(body.email)
        set_session_cookie(response, user)
        return {"usuario": to_out(user)}

    @app.post("/logout", status_code=204)
    def logout():
        response = Response(status_code=204)
        response.delete_cookie(settings.cookie_name, path="/", httponly=True, secure=settings.secure_cookie, samesite="lax")
        return response

    @app.get("/me", response_model=UsuarioRespuesta)
    def me(request: Request, db: Session = Depends(get_db)):
        user_id = read_session(request.cookies.get(settings.cookie_name), settings.auth_secret)
        user = db.get(User, user_id) if user_id else None
        if user is None or not user.active:
            return JSONResponse(status_code=401, content={"detail": "Sesión no válida o vencida."})
        return {"usuario": to_out(user)}

    @app.get("/salud")
    def salud(db: Session = Depends(get_db)):
        db.execute(text("SELECT 1"))
        return {"estado": "ok", "bd": "ok"}

    return app
