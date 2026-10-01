import unittest
from decimal import Decimal

from app.database.repository import ServiceRepository


class FakeResult:
    def __init__(
        self,
        *,
        row=None,
        rows=None,
        scalar=None,
        rowcount=1,
        error: Exception | None = None,
    ) -> None:
        self.row = row
        self.rows = rows or []
        self.scalar = scalar
        self.rowcount = rowcount
        self.error = error

    def mappings(self):
        return self

    def first(self):
        return self.row

    def scalar_one(self):
        if self.error:
            raise self.error
        return self.scalar

    def __iter__(self):
        return iter(self.rows)


class FakeTransaction:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        if error_type:
            self.rolled_back = True
        else:
            self.committed = True
        return False


class FakeSession:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.calls = []
        self.transaction = FakeTransaction()

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        return False

    def begin(self):
        return self.transaction

    def execute(self, query, parameters):
        self.calls.append((str(query), parameters))
        return self.results.pop(0)


class RepositoryTests(unittest.TestCase):
    def test_customer_lookup_uses_email_bind_parameter_and_customer_role(self):
        session = FakeSession(
            [FakeResult(row={"id": 9, "name": "Ana", "last_name": "Prueba"})]
        )
        repository = ServiceRepository(lambda: session)

        customer = repository.find_customer("  ANA@example.com ")

        self.assertEqual(customer["id"], 9)
        query, parameters = session.calls[0]
        self.assertIn("role::text = 'CUSTOMER'", query)
        self.assertIn(":email", query)
        self.assertEqual(parameters, {"email": "ANA@example.com"})

    def test_ticket_insert_uses_parameters_and_starts_in_diagnosis(self):
        session = FakeSession([FakeResult(scalar=55)])
        repository = ServiceRepository(lambda: session)

        ticket_id = repository.create_ticket(
            code="ST-123456789ABC",
            customer_id=9,
            title="Laptop falla",
            failure_description="Se apaga.",
            request_type="REPAIR",
            provisional_diagnosis="Ventilación.",
        )

        query, parameters = session.calls[0]
        self.assertEqual(ticket_id, 55)
        self.assertIn("IN_DIAGNOSIS", query)
        self.assertIn(":failure_description", query)
        self.assertEqual(parameters["customer_id"], 9)
        self.assertTrue(session.transaction.committed)

    def test_quote_and_ticket_update_share_one_transaction(self):
        session = FakeSession(
            [
                FakeResult(rowcount=1),
                FakeResult(scalar=77),
                FakeResult(),
            ]
        )
        repository = ServiceRepository(lambda: session)

        quote_id = repository.save_quote(
            ticket_id=55,
            labor_cost=Decimal("80.00"),
            parts_cost=Decimal("10.00"),
            total_amount=Decimal("90.00"),
            observations="Diagnóstico provisional.",
            parts=[
                {
                    "id": 4,
                    "quantity": 1,
                    "unit_price": Decimal("10.00"),
                    "subtotal": Decimal("10.00"),
                }
            ],
        )

        self.assertEqual(quote_id, 77)
        self.assertEqual(len(session.calls), 3)
        self.assertIn("QUOTED", session.calls[0][0])
        self.assertIn("quotes", session.calls[1][0])
        self.assertIn("quote_details", session.calls[2][0])
        self.assertTrue(session.transaction.committed)

    def test_quote_transaction_rolls_back_when_ticket_is_missing(self):
        session = FakeSession([FakeResult(rowcount=0)])
        repository = ServiceRepository(lambda: session)

        with self.assertRaisesRegex(LookupError, "ticket 55"):
            repository.save_quote(
                ticket_id=55,
                labor_cost=Decimal("80.00"),
                parts_cost=Decimal("0.00"),
                total_amount=Decimal("80.00"),
                observations="Diagnóstico provisional.",
                parts=[],
            )

        self.assertEqual(len(session.calls), 1)
        self.assertTrue(session.transaction.rolled_back)
        self.assertFalse(session.transaction.committed)

    def test_ticket_and_quote_are_created_in_one_transaction(self):
        session = FakeSession(
            [
                FakeResult(scalar=55),
                FakeResult(scalar=77),
                FakeResult(rowcount=1),
                FakeResult(),
            ]
        )
        repository = ServiceRepository(lambda: session)

        ticket_id, quote_id = repository.create_ticket_with_quote(
            ticket_code="ST-123456789ABC",
            customer_id=9,
            title="Laptop lenta",
            failure_description="Tarda en iniciar.",
            request_type="REPAIR",
            provisional_diagnosis="Unidad lenta.",
            labor_cost=Decimal("20.00"),
            parts_cost=Decimal("180.00"),
            total_amount=Decimal("200.00"),
            observations="Guía RAG simulada.",
            parts=[
                {
                    "id": 4,
                    "quantity": 1,
                    "unit_price": Decimal("180.00"),
                    "subtotal": Decimal("180.00"),
                }
            ],
        )

        self.assertEqual((ticket_id, quote_id), (55, 77))
        self.assertEqual(len(session.calls), 4)
        self.assertIn("IN_DIAGNOSIS", session.calls[0][0])
        self.assertIn("quotes", session.calls[1][0])
        self.assertIn("QUOTED", session.calls[2][0])
        self.assertIn("quote_details", session.calls[3][0])
        self.assertTrue(session.transaction.committed)

    def test_ticket_is_rolled_back_if_quote_insert_fails(self):
        session = FakeSession(
            [
                FakeResult(scalar=55),
                FakeResult(error=RuntimeError("simulated quote failure")),
            ]
        )
        repository = ServiceRepository(lambda: session)

        with self.assertRaisesRegex(RuntimeError, "simulated quote failure"):
            repository.create_ticket_with_quote(
                ticket_code="ST-123456789ABC",
                customer_id=9,
                title="Laptop lenta",
                failure_description="Tarda en iniciar.",
                request_type="REPAIR",
                provisional_diagnosis="Unidad lenta.",
                labor_cost=Decimal("20.00"),
                parts_cost=Decimal("0.00"),
                total_amount=Decimal("20.00"),
                observations="Guía RAG simulada.",
                parts=[],
            )

        self.assertEqual(len(session.calls), 2)
        self.assertTrue(session.transaction.rolled_back)
        self.assertFalse(session.transaction.committed)


if __name__ == "__main__":
    unittest.main()
