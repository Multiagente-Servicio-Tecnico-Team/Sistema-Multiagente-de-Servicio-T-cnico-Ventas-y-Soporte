from collections.abc import Callable
from decimal import Decimal
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


SessionFactory = Callable[[], Session]


class ServiceRepository:
    def __init__(self, session_factory: SessionFactory | None = None) -> None:
        if session_factory is None:
            from app.database.connection import SessionLocal

            session_factory = SessionLocal
        self._session_factory = session_factory

    def find_customer(self, email: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT id, name, last_name
            FROM users
            WHERE LOWER(email) = LOWER(:email)
              AND active IS TRUE
              AND role::text = 'CUSTOMER'
            """
        )
        with self._session_factory() as session:
            customer = (
                session.execute(query, {"email": email.strip()})
                .mappings()
                .first()
            )
        return dict(customer) if customer else None

    def create_ticket(
        self,
        *,
        code: str,
        customer_id: int,
        title: str,
        failure_description: str,
        request_type: str,
        provisional_diagnosis: str,
    ) -> int:
        query = text(
            """
            INSERT INTO tickets (
                code,
                customer_id,
                title,
                failure_description,
                request_type,
                status,
                provisional_diagnosis
            )
            VALUES (
                :code,
                :customer_id,
                :title,
                :failure_description,
                CAST(:request_type AS request_type_enum),
                CAST('IN_DIAGNOSIS' AS ticket_status_enum),
                :provisional_diagnosis
            )
            RETURNING id
            """
        )
        with self._session_factory() as session, session.begin():
            ticket_id = session.execute(
                query,
                {
                    "code": code,
                    "customer_id": customer_id,
                    "title": title,
                    "failure_description": failure_description,
                    "request_type": request_type,
                    "provisional_diagnosis": provisional_diagnosis,
                },
            ).scalar_one()
        return int(ticket_id)

    def find_spare_parts(self, search_term: str) -> list[dict[str, Any]]:
        term = search_term.strip()
        normalized_name = re.sub(r"_+", " ", term).strip()
        escaped_name = (
            normalized_name.replace("!", "!!")
            .replace("%", "!%")
            .replace("_", "!_")
        )
        query = text(
            """
            SELECT id, code, name, unit_price, current_stock
            FROM spare_parts
            WHERE active IS TRUE
              AND (
                    LOWER(code) = LOWER(:term)
                    OR LOWER(name) = LOWER(:normalized_name)
                    OR name ILIKE :pattern ESCAPE '!'
              )
            ORDER BY
                CASE
                    WHEN LOWER(code) = LOWER(:term) THEN 0
                    WHEN LOWER(name) = LOWER(:normalized_name) THEN 1
                    ELSE 2
                END,
                name
            LIMIT 5
            """
        )
        with self._session_factory() as session:
            rows = session.execute(
                query,
                {
                    "term": term,
                    "normalized_name": normalized_name,
                    "pattern": f"%{escaped_name}%",
                },
            ).mappings()
            return [dict(row) for row in rows]

    def create_ticket_with_quote(
        self,
        *,
        ticket_code: str,
        customer_id: int,
        title: str,
        failure_description: str,
        request_type: str,
        provisional_diagnosis: str,
        labor_cost: Decimal,
        parts_cost: Decimal,
        total_amount: Decimal,
        observations: str,
        parts: list[dict[str, Any]],
    ) -> tuple[int, int]:
        insert_ticket = text(
            """
            INSERT INTO tickets (
                code,
                customer_id,
                title,
                failure_description,
                request_type,
                status,
                provisional_diagnosis
            )
            VALUES (
                :code,
                :customer_id,
                :title,
                :failure_description,
                CAST(:request_type AS request_type_enum),
                CAST('IN_DIAGNOSIS' AS ticket_status_enum),
                :provisional_diagnosis
            )
            RETURNING id
            """
        )
        insert_quote = text(
            """
            INSERT INTO quotes (
                ticket_id,
                labor_cost,
                parts_cost,
                total_amount,
                status,
                observations
            )
            VALUES (
                :ticket_id,
                :labor_cost,
                :parts_cost,
                :total_amount,
                CAST('PENDING' AS quote_status_enum),
                :observations
            )
            RETURNING id
            """
        )
        update_ticket = text(
            """
            UPDATE tickets
            SET status = CAST('QUOTED' AS ticket_status_enum),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :ticket_id
            """
        )
        insert_detail = text(
            """
            INSERT INTO quote_details (
                quote_id,
                spare_part_id,
                quantity,
                unit_price,
                subtotal
            )
            VALUES (
                :quote_id,
                :spare_part_id,
                :quantity,
                :unit_price,
                :subtotal
            )
            """
        )
        with self._session_factory() as session, session.begin():
            ticket_id = session.execute(
                insert_ticket,
                {
                    "code": ticket_code,
                    "customer_id": customer_id,
                    "title": title,
                    "failure_description": failure_description,
                    "request_type": request_type,
                    "provisional_diagnosis": provisional_diagnosis,
                },
            ).scalar_one()
            quote_id = session.execute(
                insert_quote,
                {
                    "ticket_id": ticket_id,
                    "labor_cost": labor_cost,
                    "parts_cost": parts_cost,
                    "total_amount": total_amount,
                    "observations": observations,
                },
            ).scalar_one()
            updated = session.execute(update_ticket, {"ticket_id": ticket_id})
            if updated.rowcount != 1:
                raise LookupError(
                    f"No se pudo actualizar el ticket {ticket_id} a QUOTED."
                )
            for part in parts:
                session.execute(
                    insert_detail,
                    {
                        "quote_id": quote_id,
                        "spare_part_id": part["id"],
                        "quantity": part["quantity"],
                        "unit_price": part["unit_price"],
                        "subtotal": part["subtotal"],
                    },
                )
        return int(ticket_id), int(quote_id)

    def save_quote(
        self,
        *,
        ticket_id: int,
        labor_cost: Decimal,
        parts_cost: Decimal,
        total_amount: Decimal,
        observations: str,
        parts: list[dict[str, Any]],
    ) -> int:
        insert_quote = text(
            """
            INSERT INTO quotes (
                ticket_id,
                labor_cost,
                parts_cost,
                total_amount,
                status,
                observations
            )
            VALUES (
                :ticket_id,
                :labor_cost,
                :parts_cost,
                :total_amount,
                CAST('PENDING' AS quote_status_enum),
                :observations
            )
            RETURNING id
            """
        )
        update_ticket = text(
            """
            UPDATE tickets
            SET status = CAST('QUOTED' AS ticket_status_enum),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :ticket_id
            """
        )
        insert_detail = text(
            """
            INSERT INTO quote_details (
                quote_id,
                spare_part_id,
                quantity,
                unit_price,
                subtotal
            )
            VALUES (
                :quote_id,
                :spare_part_id,
                :quantity,
                :unit_price,
                :subtotal
            )
            """
        )

        with self._session_factory() as session, session.begin():
            updated = session.execute(
                update_ticket,
                {"ticket_id": ticket_id},
            )
            if updated.rowcount != 1:
                raise LookupError(
                    f"No se pudo actualizar el ticket {ticket_id} a QUOTED."
                )
            quote_id = session.execute(
                insert_quote,
                {
                    "ticket_id": ticket_id,
                    "labor_cost": labor_cost,
                    "parts_cost": parts_cost,
                    "total_amount": total_amount,
                    "observations": observations,
                },
            ).scalar_one()
            for part in parts:
                session.execute(
                    insert_detail,
                    {
                        "quote_id": quote_id,
                        "spare_part_id": part["id"],
                        "quantity": part["quantity"],
                        "unit_price": part["unit_price"],
                        "subtotal": part["subtotal"],
                    },
                )
        return int(quote_id)
