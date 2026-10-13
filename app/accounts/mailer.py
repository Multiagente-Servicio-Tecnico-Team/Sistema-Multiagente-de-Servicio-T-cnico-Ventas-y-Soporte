"""Password reset email delivery: real SMTP or a local folder (outbox) for development."""
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "email" / "templates"
SUBJECT = "Restablece tu contraseña de TechFix.AI"

_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


def render_password_reset(name: str, link: str, minutes: int) -> str:
    return _env.get_template("password_reset.html").render(name=name, link=link, minutes=minutes)


class OutboxMailer:
    """Saves each email as an HTML file in a local folder ignored by git."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def send(self, to: str, subject: str, html: str) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{datetime.now():%Y%m%d-%H%M%S-%f}-password-reset.html"
        path.write_text(f"<!-- Para: {to} | Asunto: {subject} -->\n{html}", encoding="utf-8")
        return path


class SmtpMailer:
    """Uses the repository SMTP service (SMTP_* variables)."""

    def send(self, to: str, subject: str, html: str) -> None:
        from app.email.email_service import _send_email_sync

        _send_email_sync(to, subject, html)


def build_mailer(mode: str, outbox_dir: str):
    return SmtpMailer() if mode == "smtp" else OutboxMailer(outbox_dir)


def send_password_reset(mailer, to: str, name: str, link: str, minutes: int) -> None:
    """Runs in the background. A failure is logged without the email address, link or token."""
    try:
        mailer.send(to, SUBJECT, render_password_reset(name, link, minutes))
    except Exception:  # noqa: BLE001 - the user already got the generic response
        logger.error("Could not send the password reset email.")
