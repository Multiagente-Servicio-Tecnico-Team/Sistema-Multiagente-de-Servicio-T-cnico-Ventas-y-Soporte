from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import MetaData, Table, inspect, insert, select, text
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


def ensure_schema(engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    statements = (
        """CREATE TABLE IF NOT EXISTS tickets (
            id BIGSERIAL PRIMARY KEY,
            codigo VARCHAR(40) NOT NULL UNIQUE,
            tipo_solicitud VARCHAR(120) NOT NULL,
            estado VARCHAR(40) NOT NULL DEFAULT 'En Análisis',
            cliente_id BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS presupuestos (
            id BIGSERIAL PRIMARY KEY,
            ticket_id BIGINT NOT NULL,
            cliente_id BIGINT NOT NULL,
            diagnostico TEXT NOT NULL,
            mano_obra NUMERIC(12, 2) NOT NULL,
            total NUMERIC(12, 2) NOT NULL,
            estado VARCHAR(40) NOT NULL DEFAULT 'Pendiente de aceptación',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS presupuesto_detalles (
            id BIGSERIAL PRIMARY KEY,
            presupuesto_id BIGINT NOT NULL,
            repuesto_id BIGINT,
            nombre VARCHAR(200) NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario NUMERIC(12, 2) NOT NULL,
            subtotal NUMERIC(12, 2) NOT NULL
        )""",
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def find_user_by_email(email: str, engine: Engine | None = None) -> dict[str, object] | None:
    engine = engine or get_engine()
    with engine.connect() as connection:
        table = _table(connection, "usuarios")
        email_column = _column(table, "email")
        id_column = _column(table, "id", "usuario_id")
        name_column = _column(table, "nombre", "name")
        if email_column is None or id_column is None:
            raise RuntimeError("La tabla usuarios debe tener columnas id (o usuario_id) y email")
        selected_columns = [id_column, email_column]
        if name_column is not None:
            selected_columns.append(name_column)
        row = connection.execute(
            select(*selected_columns).where(email_column.ilike(email.strip())).limit(1)
        ).mappings().first()
        return dict(row) if row else None


def create_ticket(
    user_id: object,
    category: str,
    engine: Engine | None = None,
) -> int:
    engine = engine or get_engine()
    ensure_schema(engine)
    with engine.begin() as connection:
        ticket = _table(connection, "tickets")
        ticket_id = _insert_row(
            connection,
            ticket,
            {
                "codigo": f"TCK-{uuid4().hex[:10].upper()}",
                "tipo_solicitud": category,
                "estado": "En Análisis",
                "cliente_id": user_id,
                "usuario_id": user_id,
            },
        )
    return ticket_id


def lookup_inventory(
    requested_name: str,
    quantity: int,
    engine: Engine | None = None,
) -> dict[str, object]:
    engine = engine or get_engine()
    tables = {name.casefold(): name for name in inspect(engine).get_table_names()}
    table_name = next(
        (tables[name] for name in ("repuestos", "repuesto") if name in tables),
        None,
    )
    if table_name is None:
        raise RuntimeError("No se encontró la tabla de inventario repuestos")

    with engine.connect() as connection:
        table = _table(connection, table_name)
        name_column = _column(table, "nombre", "nombre_repuesto", "articulo", "producto")
        stock_column = _column(table, "stock", "cantidad", "existencias", "disponible")
        price_column = _column(table, "precio", "precio_unitario", "costo")
        id_column = _column(table, "id", "repuesto_id")
        if name_column is None or stock_column is None or price_column is None:
            raise RuntimeError(
                f"La tabla {table_name} debe incluir nombre, stock/cantidad y precio"
            )
        rows = connection.execute(
            select(table).where(name_column.ilike(f"%{requested_name.strip()}%"))
        ).mappings().all()

    if not rows:
        return {
            "requested_name": requested_name,
            "name": requested_name,
            "quantity": quantity,
            "stock": 0,
            "unit_price": Decimal("0.00"),
            "available": False,
            "inventory_id": None,
        }

    row = next(
        (candidate for candidate in rows if str(candidate[name_column.name]).casefold() == requested_name.casefold()),
        rows[0],
    )
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


def save_quote(
    user_id: object,
    ticket_id: int,
    diagnosis: str,
    labor_cost: Decimal,
    available_parts: list[dict[str, object]],
    engine: Engine | None = None,
) -> tuple[int, Decimal]:
    engine = engine or get_engine()
    ensure_schema(engine)
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
        quotes = _table(connection, "presupuestos")
        quote_id = _insert_row(
            connection,
            quotes,
            {
                "ticket_id": ticket_id,
                "cliente_id": user_id,
                "usuario_id": user_id,
                "diagnostico": diagnosis,
                "mano_obra": labor_cost,
                "total": total,
                "estado": "Pendiente de aceptación",
            },
        )
        details = _table(connection, "presupuesto_detalles")
        for part in available_parts:
            quantity = int(part["quantity"])
            unit_price = Decimal(str(part["unit_price"]))
            _insert_row(
                connection,
                details,
                {
                    "presupuesto_id": quote_id,
                    "repuesto_id": part.get("inventory_id"),
                    "nombre": part["name"],
                    "cantidad": quantity,
                    "precio_unitario": unit_price,
                    "subtotal": unit_price * quantity,
                },
            )
    return quote_id, total