from __future__ import annotations

from decimal import Decimal
import re
import unicodedata
from uuid import uuid4

from sqlalchemy import MetaData, Table, and_, func, insert, inspect, or_, select, update
from sqlalchemy.engine import Connection, Engine

from app.database.connection import get_engine


def _table(connection: Connection, name: str) -> Table:
    return Table(name, MetaData(), autoload_with=connection)


def _column(table: Table, *names: str):
    columns = {column.name.casefold(): column for column in table.columns}
    return next((columns[name.casefold()] for name in names if name.casefold() in columns), None)


def _insert_row(connection: Connection, table: Table, values: dict[str, object]) -> int:
    row = {
        column.name: value
        for key, value in values.items()
        if (column := _column(table, key)) is not None
    }
    missing = [
        column.name
        for column in table.columns
        if not column.primary_key
        and not column.nullable
        and column.default is None
        and column.server_default is None
        and column.identity is None
        and column.name not in row
        and column.autoincrement is not True
    ]
    if missing:
        raise RuntimeError(
            f"La tabla {table.name} requiere columnas no contempladas: {', '.join(missing)}"
        )

    primary_key = next(iter(table.primary_key.columns), None)
    if primary_key is None:
        raise RuntimeError(f"La tabla {table.name} no tiene clave primaria")
    return connection.execute(
        insert(table).values(**row).returning(primary_key)
    ).scalar_one()


def find_user_by_email(email: str, engine: Engine | None = None) -> dict[str, object] | None:
    engine = engine or get_engine()
    with engine.connect() as connection:
        table = _table(connection, "users")
        email_column = _column(table, "email")
        id_column = _column(table, "id")
        name_column = _column(table, "name")
        active_column = _column(table, "active", "activo")
        if email_column is None or id_column is None:
            raise RuntimeError("La tabla users debe tener columnas id y email")
        selected_columns = [id_column, email_column]
        if name_column is not None:
            selected_columns.append(name_column)
        conditions = [func.lower(email_column) == email.strip().casefold()]
        if active_column is not None:
            conditions.append(active_column.is_(True))
        row = connection.execute(
            select(*selected_columns).where(*conditions).limit(1)
        ).mappings().first()
        return dict(row) if row else None


def create_ticket(
    user_id: object,
    product: str,
    category: str,
    symptoms: str,
    engine: Engine | None = None,
) -> int:
    engine = engine or get_engine()
    with engine.begin() as connection:
        ticket = _table(connection, "tickets")
        return _insert_row(
            connection,
            ticket,
            {
                "code": f"TCK-{uuid4().hex[:12].upper()}",
                "codigo": f"TCK-{uuid4().hex[:12].upper()}",
                "customer_id": user_id,
                "cliente_id": user_id,
                "title": f"{product} - {category}"[:200],
                "failure_description": symptoms,
                "request_type": category,
                "diagnosis_type": "NONE",
                "status": "NEW",
                "is_remote_service": False,
            },
        )


def update_ticket_intake(
    ticket_id: int,
    product: str,
    category: str,
    symptoms: str,
    engine: Engine | None = None,
) -> None:
    engine = engine or get_engine()
    with engine.begin() as connection:
        ticket = _table(connection, "tickets")
        id_column = _column(ticket, "id")
        title_column = _column(ticket, "title")
        description_column = _column(ticket, "failure_description")
        if id_column is None or title_column is None or description_column is None:
            raise RuntimeError("La tabla tickets no contiene las columnas de ingreso esperadas")
        connection.execute(
            update(ticket)
            .where(id_column == ticket_id)
            .values(
                {
                    title_column: f"{product} - {category}"[:200],
                    description_column: symptoms,
                }
            )
        )


def update_ticket_diagnosis(
    ticket_id: int,
    diagnosis: str,
    engine: Engine | None = None,
) -> None:
    engine = engine or get_engine()
    with engine.begin() as connection:
        ticket = _table(connection, "tickets")
        id_column = _column(ticket, "id")
        diagnosis_column = _column(ticket, "provisional_diagnosis")
        status_column = _column(ticket, "status", "estado")
        if id_column is None or diagnosis_column is None:
            raise RuntimeError("La tabla tickets no permite guardar el diagnóstico provisional")
        values = {diagnosis_column: diagnosis}
        if status_column is not None:
            values[status_column] = "IN_DIAGNOSIS"
        connection.execute(
            update(ticket)
            .where(id_column == ticket_id)
            .values(values)
        )


def _normalize(value: object) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", str(value).casefold())
        if unicodedata.category(character) != "Mn"
    )


def lookup_inventory(
    requested_name: str,
    quantity: int,
    engine: Engine | None = None,
) -> dict[str, object]:
    engine = engine or get_engine()
    tables = {name.casefold(): name for name in inspect(engine).get_table_names()}
    table_name = next(
        (tables[name] for name in ("spare_parts", "spare_part", "repuestos", "repuesto") if name in tables),
        None,
    )
    if table_name is None:
        raise RuntimeError("No se encontró la tabla de inventario spare_parts")

    with engine.connect() as connection:
        table = _table(connection, table_name)
        name_column = _column(table, "name", "nombre", "nombre_repuesto", "articulo", "producto")
        stock_column = _column(table, "current_stock", "stock", "cantidad", "existencias", "disponible")
        price_column = _column(table, "unit_price", "precio", "precio_unitario", "costo")
        id_column = _column(table, "id", "spare_part_id", "repuesto_id")
        active_column = _column(table, "active", "activo")
        if name_column is None or stock_column is None or price_column is None:
            raise RuntimeError(
                f"La tabla {table_name} debe incluir nombre, inventario y precio unitario"
            )
        query = select(table)
        if active_column is not None:
            query = query.where(active_column.is_(True))
        rows = connection.execute(query).mappings().all()

    requested = _normalize(requested_name)
    requested_tokens = set(re.findall(r"[a-z0-9]+", requested))
    matches = []
    for candidate in rows:
        item_name = str(candidate[name_column.name])
        normalized_name = _normalize(item_name)
        item_tokens = set(re.findall(r"[a-z0-9]+", normalized_name))
        score = len(requested_tokens & item_tokens) / max(len(requested_tokens), 1)
        if requested in normalized_name or normalized_name in requested:
            score = 1.0
        if score >= 0.5:
            matches.append((score, candidate))

    if not matches:
        return {
            "requested_name": requested_name,
            "name": requested_name,
            "quantity": quantity,
            "stock": 0,
            "unit_price": Decimal("0.00"),
            "available": False,
            "inventory_id": None,
        }

    _, row = max(matches, key=lambda match: match[0])
    stock = int(row[stock_column.name] or 0)
    return {
        "requested_name": requested_name,
        "name": str(row[name_column.name]),
        "quantity": quantity,
        "stock": stock,
        "unit_price": Decimal(str(row[price_column.name] or 0)),
        "available": stock >= quantity,
        "inventory_id": row[id_column.name] if id_column is not None else None,
    }


def search_inventory_options(query: str, limit: int = 12, engine: Engine | None = None) -> list[dict[str, object]]:
    """Busca opciones por código, nombre, categoría o descripción; precios/stock vienen de BD."""
    engine = engine or get_engine()
    with engine.connect() as connection:
        table = _table(connection, "spare_parts")
        name_col = _column(table, "name", "nombre")
        code_col = _column(table, "code", "codigo")
        category_col = _column(table, "category", "categoria")
        description_col = _column(table, "description", "descripcion")
        stock_col = _column(table, "current_stock", "stock")
        price_col = _column(table, "unit_price", "precio")
        active_col = _column(table, "active", "activo")
        id_col = _column(table, "id")
        if name_col is None or stock_col is None or price_col is None:
            raise RuntimeError("El inventario requiere nombre, stock y precio")
        query_norm = _normalize(query)
        terms = [term for term in re.findall(r"[a-z0-9]+", query_norm) if len(term) > 2 and term not in {"memoria", "gamer", "producto", "comprar", "quisiera", "quiero", "laptop", "mouse", "para"}]
        predicates = []
        for term in terms:
            like = f"%{term}%"
            for col in (name_col, code_col, category_col, description_col):
                if col is not None:
                    predicates.append(func.lower(col).like(like))
        stmt = select(table)
        if active_col is not None:
            stmt = stmt.where(active_col.is_(True))
        if predicates:
            stmt = stmt.where(or_(*predicates))
        if name_col is not None:
            normalized_candidate = func.lower(func.coalesce(name_col, ""))
            for term in terms:
                stmt = stmt.order_by(normalized_candidate.like(f"%{term}%").desc())
            stmt = stmt.order_by(name_col.asc())
        stmt = stmt.limit(limit)
        rows = connection.execute(stmt).mappings().all()
        return [
            {
                "spare_part_id": row[id_col.name] if id_col is not None else None,
                "code": row[code_col.name] if code_col is not None else "",
                "name": row[name_col.name],
                "category": row[category_col.name] if category_col is not None else "",
                "description": row[description_col.name] if description_col is not None else "",
                "unit_price": Decimal(str(row[price_col.name] or 0)),
                "current_stock": int(row[stock_col.name] or 0),
            }
            for row in rows
        ]


def create_customer_ticket(user_id: object, request_type: str, title: str, details: str, engine: Engine | None = None) -> dict[str, object]:
    engine = engine or get_engine()
    with engine.begin() as connection:
        table = _table(connection, "tickets")
        ticket_id = _insert_row(connection, table, {
            "code": f"TCK-{uuid4().hex[:10].upper()}", "customer_id": user_id,
            "title": title[:200], "failure_description": details,
            "request_type": request_type, "diagnosis_type": "NONE", "status": "NEW", "is_remote_service": False,
        })
        pk = next(iter(table.primary_key.columns))
        row = connection.execute(select(table).where(pk == ticket_id)).mappings().one()
        return {"id": ticket_id, "code": row.get("code")}


def search_supplier_options(query: str, engine: Engine | None = None) -> list[dict[str, object]]:
    engine = engine or get_engine()
    with engine.connect() as connection:
        table = _table(connection, "suppliers")
        active = _column(table, "active", "activo")
        stmt = select(table)
        if active is not None:
            stmt = stmt.where(active.is_(True))
        rows = connection.execute(stmt.limit(20)).mappings().all()
        return [{"id": row.get("id"), "name": row.get("name"), "delivery_lead_days": row.get("delivery_lead_days")} for row in rows]


def create_accepted_quote(ticket_id: int, customer_id: int, quote_type: str, labor_cost: Decimal, items: list[dict[str, object]], observations: str = "", engine: Engine | None = None) -> dict[str, object]:
    engine = engine or get_engine()
    allowed = {"REPAIR", "DIRECT_SALE", "PC_BUILD"}
    if quote_type not in allowed:
        raise ValueError(f"Tipo de cotización no permitido: {quote_type}")
    labor = Decimal(str(labor_cost)).quantize(Decimal("0.01"))
    parts = sum((Decimal(str(item["unit_price"])) * int(item["quantity"]) for item in items), Decimal("0.00")).quantize(Decimal("0.01"))
    total = labor + parts
    with engine.begin() as connection:
        tickets = _table(connection, "tickets")
        ticket_key = _column(tickets, "id")
        owner_key = _column(tickets, "customer_id")
        if connection.execute(select(ticket_key).where(and_(ticket_key == ticket_id, owner_key == customer_id)).with_for_update()).first() is None:
            raise RuntimeError("El ticket no pertenece al cliente actual")
        quotes = _table(connection, "quotes")
        quote_id = _insert_row(connection, quotes, {
            "ticket_id": ticket_id, "quote_type": quote_type, "labor_cost": labor,
            "parts_cost": parts, "total_amount": total, "status": "ACCEPTED", "observations": observations,
        })
        details = _table(connection, "quote_details")
        quote_status = _column(quotes, "status")
        if quote_status is not None:
            connection.execute(update(quotes).where(_column(quotes, "id") == quote_id).values({quote_status: "ACCEPTED"}))
        for item in items:
            price, quantity = Decimal(str(item["unit_price"])), int(item["quantity"])
            spare_part_id = item.get("spare_part_id")
            if spare_part_id is not None:
                inventory = _table(connection, "spare_parts")
                inventory_id = _column(inventory, "id")
                stock_col = _column(inventory, "current_stock", "stock")
                active_col = _column(inventory, "active", "activo")
                inventory_query = select(inventory).where(inventory_id == spare_part_id).with_for_update()
                if active_col is not None:
                    inventory_query = inventory_query.where(active_col.is_(True))
                stock_row = connection.execute(inventory_query).mappings().first()
                if stock_row is None:
                    raise RuntimeError(f"El producto {item.get('name', spare_part_id)} ya no está activo en inventario")
                if stock_col is not None and int(stock_row[stock_col.name] or 0) < quantity:
                    raise RuntimeError(f"Stock insuficiente para {item.get('name', spare_part_id)}; consulta una alternativa actualizada")
            _insert_row(connection, details, {
                "quote_id": quote_id, "spare_part_id": item.get("spare_part_id"),
                "custom_item_name": item.get("custom_item_name") or item.get("name"),
                "quantity": quantity, "unit_price": price, "subtotal": price * quantity,
            })
        status = _column(tickets, "status")
        connection.execute(update(tickets).where(ticket_key == ticket_id).values({status: "QUOTED"}))
    return {"id": quote_id, "total_amount": total}


def cancel_ticket(ticket_id: int, customer_id: int, engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    with engine.begin() as connection:
        table = _table(connection, "tickets")
        connection.execute(update(table).where(and_(_column(table, "id") == ticket_id, _column(table, "customer_id") == customer_id)).values({_column(table, "status"): "CANCELLED"}))


def create_pending_payment(ticket_id: int, quote_id: int, customer_id: int, amount: Decimal, engine: Engine | None = None) -> dict[str, object]:
    engine = engine or get_engine()
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValueError("El esquema requiere que el importe de pago sea mayor a cero")
    code = f"PAY-{uuid4().hex[:10].upper()}"
    with engine.begin() as connection:
        table = _table(connection, "payments")
        existing = connection.execute(select(table).where(and_(_column(table, "ticket_id") == ticket_id, _column(table, "quote_id") == quote_id)).limit(1)).mappings().first()
        if existing:
            return {"id": existing["id"], "payment_code": existing["payment_code"], "status": existing["status"]}
        payment_id = _insert_row(connection, table, {"ticket_id": ticket_id, "quote_id": quote_id, "customer_id": customer_id, "payment_code": code, "amount": amount, "status": "PENDING"})
        tickets = _table(connection, "tickets")
        connection.execute(update(tickets).where(_column(tickets, "id") == ticket_id).values({_column(tickets, "status"): "PAYMENT_PENDING"}))
    return {"id": payment_id, "payment_code": code, "status": "PENDING"}


def create_logistics_record(ticket_id: int, mode: str, courier_company: str | None = None, shipping_address: str | None = None, engine: Engine | None = None) -> dict[str, object]:
    if mode not in {"PHYSICAL_STORE", "COURIER_SHIPMENT"}:
        raise ValueError("Modalidad logística inválida")
    engine = engine or get_engine()
    with engine.begin() as connection:
        table = _table(connection, "logistics_records")
        id_col = _column(table, "id")
        existing = connection.execute(select(id_col).where(_column(table, "ticket_id") == ticket_id).limit(1)).scalar_one_or_none()
        if existing:
            row = connection.execute(select(table).where(id_col == existing)).mappings().one()
            return {"id": existing, "status": row.get("status"), "mode": row.get("mode")}
        row_id = _insert_row(connection, table, {"ticket_id": ticket_id, "mode": mode, "status": "PENDING_RECEIPT", "courier_company": courier_company, "shipping_address": shipping_address})
    return {"id": row_id, "status": "PENDING_RECEIPT", "mode": mode}


def issue_warranty(ticket_id: int, quote_id: int, customer_id: int, item_name: str, engine: Engine | None = None) -> dict[str, object]:
    from sqlalchemy import text
    engine = engine or get_engine()
    code = f"WAR-{uuid4().hex[:10].upper()}"
    with engine.begin() as connection:
        table = _table(connection, "warranties")
        ticket_col, quote_col = _column(table, "ticket_id"), _column(table, "quote_id")
        existing = connection.execute(select(table).where(and_(ticket_col == ticket_id, quote_col == quote_id)).limit(1)).mappings().first()
        if existing:
            return dict(existing)
        result = connection.execute(text("""INSERT INTO warranties (ticket_id, quote_id, customer_id, warranty_code, item_or_service_name, warranty_months, start_date, end_date, status) VALUES (:ticket_id,:quote_id,:customer_id,:code,:item,3,CURRENT_DATE,(CURRENT_DATE + INTERVAL '3 months')::date,'ACTIVE') RETURNING id,warranty_code,start_date,end_date,status"""), {"ticket_id": ticket_id, "quote_id": quote_id, "customer_id": customer_id, "code": code, "item": item_name}).mappings().one()
        return dict(result)


def lookup_warranty(warranty_code: str, engine: Engine | None = None) -> dict[str, object] | None:
    engine = engine or get_engine()
    with engine.connect() as connection:
        table = _table(connection, "warranties")
        code = _column(table, "warranty_code")
        row = connection.execute(select(table).where(code == warranty_code.strip()).limit(1)).mappings().first()
        return dict(row) if row else None


def get_customer_ticket(ticket_id: int, customer_id: int, engine: Engine | None = None) -> dict[str, object] | None:
    engine = engine or get_engine()
    with engine.connect() as connection:
        table = _table(connection, "tickets")
        row = connection.execute(select(table).where(and_(_column(table, "id") == ticket_id, _column(table, "customer_id") == customer_id)).limit(1)).mappings().first()
        return dict(row) if row else None


def create_warranty_claim(warranty_id: int, ticket_id: int, customer_id: int, reason: str, engine: Engine | None = None) -> dict[str, object]:
    engine = engine or get_engine()
    code = f"CLM-{uuid4().hex[:10].upper()}"
    with engine.begin() as connection:
        warranties = _table(connection, "warranties")
        warranty = connection.execute(select(warranties).where(and_(_column(warranties, "id") == warranty_id, _column(warranties, "customer_id") == customer_id)).with_for_update()).mappings().first()
        if warranty is None:
            raise RuntimeError("La póliza no pertenece al cliente actual")
        claims = _table(connection, "warranty_claims")
        claim_id = _insert_row(connection, claims, {"warranty_id": warranty_id, "ticket_id": ticket_id, "claim_code": code, "reason": reason, "status": "IN_REVIEW"})
        tickets = _table(connection, "tickets")
        connection.execute(update(tickets).where(_column(tickets, "id") == ticket_id).values({_column(tickets, "status"): "WARRANTY_IN_REVIEW"}))
    return {"id": claim_id, "claim_code": code, "status": "IN_REVIEW"}


def save_quote(
    ticket_id: int,
    diagnosis: str,
    labor_cost: Decimal,
    available_parts: list[dict[str, object]],
    engine: Engine | None = None,
) -> tuple[int, Decimal]:
    engine = engine or get_engine()
    labor_cost = Decimal(str(labor_cost)).quantize(Decimal("0.01"))
    parts_total = sum(
        (
            Decimal(str(part["unit_price"])) * int(part["quantity"])
            for part in available_parts
        ),
        Decimal("0.00"),
    )
    parts_total = parts_total.quantize(Decimal("0.01"))
    total = labor_cost + parts_total
    with engine.begin() as connection:
        quotes = _table(connection, "quotes")
        quote_id = _insert_row(
            connection,
            quotes,
            {
                "ticket_id": ticket_id,
                "observations": diagnosis,
                "diagnostico": diagnosis,
                "labor_cost": labor_cost,
                "mano_obra": labor_cost,
                "parts_cost": parts_total,
                "total_amount": total,
                "total": total,
                "status": "PENDING",
                "estado": "Pendiente de aceptación",
            },
        )
        details = _table(connection, "quote_details")
        for part in available_parts:
            quantity = int(part["quantity"])
            unit_price = Decimal(str(part["unit_price"]))
            _insert_row(
                connection,
                details,
                {
                    "quote_id": quote_id,
                    "presupuesto_id": quote_id,
                    "spare_part_id": part["inventory_id"],
                    "repuesto_id": part.get("inventory_id"),
                    "name": part["name"],
                    "nombre": part["name"],
                    "quantity": quantity,
                    "cantidad": quantity,
                    "unit_price": unit_price,
                    "precio_unitario": unit_price,
                    "subtotal": unit_price * quantity,
                },
            )
        tickets = _table(connection, "tickets")
        ticket_key = _column(tickets, "id")
        ticket_status = _column(tickets, "status", "estado")
        if ticket_key is not None and ticket_status is not None:
            connection.execute(
                update(tickets)
                .where(ticket_key == ticket_id)
                .values({ticket_status: "QUOTED"})
            )
    return quote_id, total


def create_ticket_with_quote(
    user_id: object,
    product: str,
    category: str,
    symptoms: str,
    diagnosis: str,
    labor_cost: Decimal,
    available_parts: list[dict[str, object]],
    engine: Engine | None = None,
) -> tuple[int, int, Decimal]:
    engine = engine or get_engine()
    labor_cost = Decimal(str(labor_cost)).quantize(Decimal("0.01"))
    parts_total = sum(
        (
            Decimal(str(part["unit_price"])) * int(part["quantity"])
            for part in available_parts
        ),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    total = labor_cost + parts_total

    with engine.begin() as connection:
        tickets = _table(connection, "tickets")
        ticket_id = _insert_row(
            connection,
            tickets,
            {
                "code": f"TCK-{uuid4().hex[:12].upper()}",
                "customer_id": user_id,
                "title": f"{product} - {category}"[:200],
                "failure_description": symptoms,
                "provisional_diagnosis": diagnosis,
                "status": "IN_DIAGNOSIS",
            },
        )
        quotes = _table(connection, "quotes")
        quote_id = _insert_row(
            connection,
            quotes,
            {
                "ticket_id": ticket_id,
                "labor_cost": labor_cost,
                "parts_cost": parts_total,
                "total_amount": total,
                "status": "PENDING",
                "observations": diagnosis,
            },
        )
        details = _table(connection, "quote_details")
        for part in available_parts:
            quantity = int(part["quantity"])
            unit_price = Decimal(str(part["unit_price"]))
            _insert_row(
                connection,
                details,
                {
                    "quote_id": quote_id,
                    "spare_part_id": part["inventory_id"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": unit_price * quantity,
                },
            )
        ticket_key = _column(tickets, "id")
        ticket_status = _column(tickets, "status")
        connection.execute(
            update(tickets)
            .where(ticket_key == ticket_id)
            .values({ticket_status: "QUOTED"})
        )

    return ticket_id, quote_id, total
