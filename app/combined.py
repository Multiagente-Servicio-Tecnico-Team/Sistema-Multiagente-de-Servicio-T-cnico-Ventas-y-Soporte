"""Punto de entrada FastAPI con cuentas y chat bajo el mismo origen."""

from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from app.accounts.api import create_app as create_accounts_app
from app.accounts.config import Settings as AccountSettings
from app.accounts.session import SessionGuard
from app.main import create_app as create_chat_app


def create_app(
    *,
    settings: AccountSettings | None = None,
    session_factory: sessionmaker | None = None,
    mailer=None,
    chat_app: FastAPI | None = None,
) -> FastAPI:
    load_dotenv()
    shared_settings = settings or AccountSettings.from_env()
    accounts_app = create_accounts_app(
        settings=shared_settings,
        session_factory=session_factory,
        mailer=mailer,
    )
    shared_session_factory = accounts_app.state.session_factory

    application = (
        chat_app
        if chat_app is not None
        else create_chat_app(
            session_guard=SessionGuard(shared_settings, shared_session_factory)
        )
    )
    application.mount("/auth", accounts_app)
    return application
