import asyncio
import os

from dotenv import load_dotenv

from app.email.email_service import render_ticket_created, send_email


load_dotenv()


async def main():
    html = render_ticket_created(
        nombre_cliente="José",
        ticket_id=153,
        tipo_solicitud="Soporte técnico",
        estado="Pendiente",
    )

    await send_email(
        destinatario=os.getenv("TEST_EMAIL_TO"),
        asunto="Ticket #153 registrado",
        html=html,
    )

    print("Correo enviado correctamente de forma asíncrona.")


asyncio.run(main())