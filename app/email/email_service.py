import asyncio # programacion asincorna
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader


# Cargar variables de entorno desde el archivo .env
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


# Ruta de la carpeta donde se encuentran las plantillas HTML
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Configuración de Jinja2
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
)


def render_ticket_created(
    nombre_cliente: str,
    ticket_id: int,
    tipo_solicitud: str,
    estado: str,
) -> str:
    """Genera el HTML del correo de creación de ticket."""

    template = env.get_template("ticket_created.html")

    return template.render(
        nombre_cliente=nombre_cliente,
        ticket_id=ticket_id,
        tipo_solicitud=tipo_solicitud,
        estado=estado,
    )


def _send_email_sync(
    destinatario: str,
    asunto: str,
    html: str,
) -> None:
    """Realiza el envío SMTP del correo."""

    mensaje = EmailMessage()

    mensaje["From"] = SMTP_USER
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto

    # Versión de texto para clientes que no soporten HTML
    mensaje.set_content(
        "Este correo requiere un cliente compatible con HTML."
    )

    # Agregar el contenido HTML
    mensaje.add_alternative(html, subtype="html")

    # Conectarse al servidor SMTP de Gmail
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(mensaje)


async def send_email(
    destinatario: str,
    asunto: str,
    html: str,
) -> None:
    """Envía un correo de forma asíncrona."""

    await asyncio.to_thread(
        _send_email_sync,
        destinatario,
        asunto,
        html,
    )