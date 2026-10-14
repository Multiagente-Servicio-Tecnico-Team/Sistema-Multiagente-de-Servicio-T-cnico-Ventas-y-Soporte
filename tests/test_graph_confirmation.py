import unittest
from decimal import Decimal
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from app.agents.orquestador.agentes.customer_service import customer_service_node, ticket_intake_node
from app.agents.orquestador.agentes.sales import sales_node
from app.agents.orquestador.graph.state import IntakeResult
from app.agents.orquestador.graph.supervisor import _supervisor_route


class AgentFlowTests(unittest.TestCase):
    def test_ram_price_question_is_extracted_without_ticket_confirmation(self):
        from app.agents.orquestador.agentes.customer_service import _ram_price_inquiry

        result = _ram_price_inquiry("quiero una ram 8 gb ddr4 que precio tienen?")
        self.assertEqual(result["request_type"], "SALE")
        self.assertTrue(result["price_inquiry"])
        self.assertEqual(result["requested_items"][0]["description"], "RAM DDR4 8GB")
        self.assertEqual(result["phase"], "inventory_checked")
        self.assertEqual(result["next_agent"], "sales")

    def test_warehouse_filters_ram_by_capacity_generation_and_brand(self):
        from app.agents.orquestador.agentes.warehouse import warehouse_node

        catalog = [
            {"spare_part_id": 1, "code": "RAM-K-8", "name": "RAM desktop DDR4 8GB Kingston", "category": "RAM Desktop", "description": "DDR4 UDIMM 8GB", "unit_price": Decimal("20"), "current_stock": 5},
            {"spare_part_id": 2, "code": "RAM-C-8", "name": "RAM desktop DDR4 8GB Crucial", "category": "RAM Desktop", "description": "DDR4 UDIMM 8GB", "unit_price": Decimal("19"), "current_stock": 5},
            {"spare_part_id": 3, "code": "RAM-K-16", "name": "RAM desktop DDR4 16GB Kingston", "category": "RAM Desktop", "description": "DDR4 UDIMM 16GB", "unit_price": Decimal("38"), "current_stock": 5},
            {"spare_part_id": 4, "code": "SSD-K-8", "name": "SSD Kingston 8GB", "category": "Almacenamiento", "description": "DDR4", "unit_price": Decimal("30"), "current_stock": 5},
        ]
        with patch("app.agents.orquestador.agentes.warehouse.search_inventory_options", return_value=catalog):
            result = warehouse_node({"requested_items": [{"description": "RAM DDR4 8GB Kingston", "quantity": 1}]})

        options = result["inventory"][0]["options"]
        self.assertEqual([option["spare_part_id"] for option in options], [1])

    def test_price_inquiry_can_refine_options_to_kingston_then_laptop(self):
        from app.agents.orquestador.agentes.sales import sales_node

        options = [
            {"name": "RAM desktop DDR4 8GB Kingston", "code": "RAM-K-D", "category": "RAM Desktop", "unit_price": Decimal("20"), "current_stock": 5, "option_number": 1},
            {"name": "RAM laptop SODIMM DDR4 8GB Kingston", "code": "RAM-K-L", "category": "RAM Laptop", "unit_price": Decimal("22"), "current_stock": 4, "option_number": 2},
            {"name": "RAM laptop SODIMM DDR4 8GB Crucial", "code": "RAM-C-L", "category": "RAM Laptop", "unit_price": Decimal("21"), "current_stock": 5, "option_number": 3},
        ]
        state = {"phase": "select_item", "price_inquiry": True, "pending_description": "RAM DDR4 8GB", "pending_options": options, "current_message": "marca kingston para la ram"}
        kingston = sales_node(state)
        self.assertEqual(len(kingston["pending_options"]), 2)
        laptop = sales_node({**state, **kingston, "current_message": "para laptop"})
        self.assertEqual(len(laptop["pending_options"]), 1)
        self.assertIn("laptop", laptop["pending_options"][0]["name"].casefold())

    def test_price_inquiry_laptop_filter_handles_null_category(self):
        from app.agents.orquestador.agentes.sales import sales_node

        state = {
            "phase": "select_item", "price_inquiry": True, "pending_description": "RAM DDR4 8GB",
            "current_message": "para laptop", "pending_options": [
                {"name": "Memoria RAM DDR4 8GB Kingston", "category": None, "unit_price": Decimal("26"), "current_stock": 4, "option_number": 1},
                {"name": "RAM laptop SODIMM DDR4 8GB Kingston", "category": "RAM Laptop", "unit_price": Decimal("21.60"), "current_stock": 4, "option_number": 2},
            ],
        }
        result = sales_node(state)
        self.assertEqual(len(result["pending_options"]), 1)
        self.assertIn("laptop", result["pending_options"][0]["name"].casefold())

    def test_selecting_price_inquiry_item_shows_preliminary_quote(self):
        from app.agents.orquestador.agentes.sales import sales_node

        result = sales_node({
            "phase": "select_item", "price_inquiry": True, "pending_description": "RAM DDR4 8GB",
            "current_message": "2", "pending_options": [
                {"name": "RAM laptop SODIMM DDR4 8GB Kingston", "spare_part_id": 12, "unit_price": Decimal("21.60"), "current_stock": 6, "option_number": 2},
            ],
        })
        self.assertEqual(result["phase"], "quote_review")
        self.assertEqual(result["total"], Decimal("21.60"))
        self.assertIn("Aceptas esta cotización", result["response"])
        self.assertFalse(result["pending_options"])

    def test_accepting_price_inquiry_creates_ticket_then_quote(self):
        from app.agents.orquestador.agentes.sales import sales_node

        state = {
            "phase": "quote_acceptance", "current_message": "si", "customer_id": 12,
            "request_type": "SALE", "quote_type": "DIRECT_SALE", "labor_cost": Decimal("0"),
            "selected_items": [{"spare_part_id": 12, "name": "RAM Kingston DDR4 8GB", "quantity": 1, "unit_price": Decimal("21.60")}],
        }
        with patch("app.agents.orquestador.agentes.sales.create_customer_ticket", return_value={"id": 91, "code": "TCK-PRICE"}) as ticket, patch(
            "app.agents.orquestador.agentes.sales.create_accepted_quote", return_value={"id": 33, "total_amount": Decimal("21.60")}
        ) as quote:
            result = sales_node(state)

        ticket.assert_called_once()
        quote.assert_called_once()
        self.assertEqual(result["ticket_id"], 91)
        self.assertEqual(result["quote_id"], 33)
        self.assertEqual(result["phase"], "payment")

    def test_sale_intake_confirmation_creates_ticket_then_routes_to_sales(self):
        state = {
            "user_id": None, "customer_id": None, "intent": "SALE", "request_type": "SALE",
            "product": "RAM SODIMM DDR4 16GB y Mouse Gamer Logitech",
            "requested_items": [{"description": "RAM SODIMM DDR4 16GB", "quantity": 1}, {"description": "Mouse Gamer Logitech", "quantity": 1}],
            "phase": "intake_confirmation", "messages": [HumanMessage(content="si")],
        }
        with patch("app.agents.orquestador.agentes.customer_service.create_customer_ticket", return_value={"id": 101, "code": "TCK-SALE"}) as create_ticket:
            result = customer_service_node(state)

        create_ticket.assert_called_once()
        self.assertEqual(result["request_type"], "SALE")
        self.assertEqual(result["ticket_id"], 101)
        self.assertEqual(result["phase"], "inventory_checked")
        self.assertEqual(result["next_agent"], "sales")
        self.assertEqual(_supervisor_route(result), "sales")

    def test_sales_offers_all_multiple_options_and_preserves_other_items_after_choice(self):
        ram = {"spare_part_id": 1, "name": "RAM Kingston 16GB", "unit_price": Decimal("48"), "current_stock": 4}
        crucial = {"spare_part_id": 2, "name": "RAM Crucial 16GB", "unit_price": Decimal("52"), "current_stock": 2}
        mouse = {"spare_part_id": 3, "name": "Mouse Gamer Logitech G203", "unit_price": Decimal("24"), "current_stock": 6}
        state = {
            "intent": "SALE", "request_type": "SALE", "ticket_id": 101, "customer_id": 12,
            "requested_items": [{"description": "RAM SODIMM DDR4 16GB", "quantity": 1}, {"description": "Mouse Gamer Logitech", "quantity": 1}],
            "inventory": [
                {"description": "RAM SODIMM DDR4 16GB", "requested_quantity": 1, "options": [ram, crucial]},
                {"description": "Mouse Gamer Logitech", "requested_quantity": 1, "options": [mouse]},
            ],
        }
        preview = sales_node(state)
        self.assertEqual(preview["phase"], "select_item")
        self.assertIn("RAM Kingston 16GB", preview["response"])
        self.assertIn("RAM Crucial 16GB", preview["response"])
        choice_state = {**state, **preview, "phase": "select_item", "messages": [HumanMessage(content="2")]}
        with patch("app.agents.orquestador.agentes.sales._prepare_quote", side_effect=lambda current: {"phase": "quote_review", "selected_items": current["selected_items"], "total": sum((item["unit_price"] * item["quantity"] for item in current["selected_items"]), Decimal("0"))}):
            choice_result = sales_node(choice_state)
        self.assertEqual(choice_result["phase"], "quote_review")
        self.assertEqual({item["spare_part_id"] for item in choice_result["selected_items"]}, {2, 3})
        self.assertEqual(choice_result["total"], Decimal("76.00"))

    def test_intake_creates_sale_ticket_as_sale_and_routes_to_warehouse_through_sales(self):
        from app.agents.orquestador.agentes.customer_service import ticket_intake_node
        with patch("app.agents.orquestador.agentes.customer_service.create_customer_ticket", return_value={"id": 102, "code": "TCK-SALE2"}) as create_ticket:
            result = ticket_intake_node({"user_id": 5, "request_type": "SALE", "product": "RAM + mouse", "requested_items": []})
        create_ticket.assert_called_once()
        self.assertIn("Venta Directa", create_ticket.call_args.args[2])
        self.assertEqual(result["next_agent"], "sales")

    def test_unavailable_item_is_not_silently_quoted(self):
        result = sales_node({
            "intent": "SALE", "requested_items": [{"description": "GPU XYZ", "quantity": 1}],
            "inventory": [{"description": "GPU XYZ", "requested_quantity": 1, "options": [{"name": "GPU XYZ", "current_stock": 0, "unit_price": Decimal("99")}]}],
        })
        self.assertEqual(result["phase"], "procurement_review")
        self.assertTrue(result["awaiting_input"])
        self.assertIn("precios de proveedor confirmados", result["response"])

    def test_warehouse_filters_catalog_to_exact_form_factor_and_product_kind(self):
        from app.agents.orquestador.agentes.warehouse import warehouse_node

        inventory = warehouse_node({"requested_items": [
            {"description": "RAM SODIMM DDR4 16GB", "quantity": 1},
            {"description": "Mouse Gamer Logitech", "quantity": 1},
        ]})["inventory"]
        ram_codes = [item["code"] for item in inventory[0]["options"]]
        mouse_options = inventory[1]["options"]
        self.assertTrue(ram_codes)
        self.assertTrue(all("SODIMM" in item["name"].upper() for item in inventory[0]["options"]))
        self.assertEqual([item["code"] for item in mouse_options], ["PER-MOU-LOG-G203"])

    def test_supervisor_keeps_sales_turns_on_select_and_acceptance_phases(self):
        self.assertEqual(_supervisor_route({"phase": "select_item", "next_agent": "sales", "awaiting_input": True}), "sales")
        self.assertEqual(_supervisor_route({"phase": "quote_acceptance", "next_agent": "sales", "awaiting_input": True}), "sales")


    def test_intake_routes_to_ticket_intake_before_ticket_creation(self):
        intake = IntakeResult(
            intent="REPAIR",
            category="Soporte tÃ©cnico",
            product="Laptop HP Victus",
            symptoms="Se recalienta y estÃ¡ lenta",
            support_domain="HARDWARE",
        )
        with patch(
            "app.agents.orquestador.agentes.customer_service.invoke_structured_output",
            return_value=intake,
        ):
            result = customer_service_node(
                {"user_id": 12, "messages": [HumanMessage(content="Mi laptop se recalienta")]}
            )

        self.assertEqual(result["request_type"], "REPAIR")
        self.assertEqual(result["next_agent"], "ticket_intake")
        self.assertNotIn("ticket_id", result)
        self.assertEqual(_supervisor_route(result), "ticket_intake")

    def test_ticket_intake_creates_ticket_then_routes_to_hardware(self):
        state = {
            "user_id": 12,
            "intent": "REPAIR",
            "request_type": "REPAIR",
            "intent": "REPAIR",
            "intent": "REPAIR",
            "support_domain": "HARDWARE",
            "product": "Laptop HP Victus",
            "symptoms": "Se recalienta",
        }
        with patch(
            "app.agents.orquestador.agentes.customer_service.create_ticket",
            return_value={"id": 91, "code": "TCK-TEST"},
        ) as create_ticket:
            result = ticket_intake_node(state)

        create_ticket.assert_called_once()
        self.assertEqual(result["ticket_id"], 91)
        self.assertEqual(result["next_agent"], "hardware_support")
        self.assertEqual(_supervisor_route(result), "hardware_support")

    def test_customer_service_preserves_spanish_symptom_summary(self):
        intake = IntakeResult(
            intent="REPAIR",
            category="Soporte tÃ©cnico",
            product="Lenovo KK503",
            symptoms="Se sobrecalienta durante la carga y el uso, con un zumbido fuerte.",
            support_domain="HARDWARE",
        )
        with patch(
            "app.agents.orquestador.agentes.customer_service.invoke_structured_output",
            return_value=intake,
        ):
            result = customer_service_node(
                {
                    "user_id": 12,
                    "messages": [HumanMessage(content="Overheats quickly. Lenovo KK503.")],
                }
            )

        self.assertEqual(
            result["symptoms"],
            "Se sobrecalienta durante la carga y el uso, con un zumbido fuerte.",
        )

    def test_sales_previews_catalog_item_without_persisting_quote(self):
        part = {
            "spare_part_id": 22,
            "code": "MISC-THERM-MX4-4G",
            "name": "Pasta TÃ©rmica Arctic MX-4 4g",
            "category": "Mantenimiento",
            "description": "Pasta tÃ©rmica para CPU/GPU",
            "unit_price": Decimal("9.50"),
            "current_stock": 30,
            "available_quantity": 1,
        }
        state = {
            "intent": "REPAIR",
            "request_type": "REPAIR",
            "ticket_id": 91,
            "customer_id": 12,
            "product": "Laptop HP Victus",
            "symptoms": "Se recalienta y estÃ¡ lenta",
            "diagnosis": "Inspeccionar refrigeraciÃ³n; no hay diagnÃ³stico fÃ­sico confirmado.",
            "requested_items": [{"description": "Pasta tÃ©rmica Arctic MX-4", "quantity": 1}],
            "inventory": [
                {
                    "description": "Pasta tÃ©rmica Arctic MX-4",
                    "requested_item": {"description": "Pasta tÃ©rmica Arctic MX-4", "quantity": 1},
                    "requested_quantity": 1,
                    "options": [part],
                }
            ],
            "sales_stage": "inventory_checked",
            "quote_type": "REPAIR",
            "labor_cost": Decimal("35.00"),
        }

        result = sales_node(state)

        self.assertTrue(result["awaiting_input"])
        self.assertNotIn("quote_id", result)
        self.assertEqual(result["total"], Decimal("44.50"))
        self.assertIn("no registrado", result["response"])

    def test_customer_acceptance_persists_quote_and_hands_off_to_payments(self):
        quote = {"id": 27, "total_amount": Decimal("44.50")}
        state = {
            "awaiting_input": True,
            "phase": "quote_acceptance",
            "messages": [HumanMessage(content="si, acepto")],
            "ticket_id": 91,
            "customer_id": 12,
            "request_type": "REPAIR",
            "quote_type": "REPAIR",
            "labor_cost": Decimal("35.00"),
            "selected_items": [
                {
                    "spare_part_id": 22,
                    "name": "Pasta TÃ©rmica Arctic MX-4 4g",
                    "quantity": 1,
                    "unit_price": Decimal("9.50"),
                }
            ],
        }
        with patch(
            "app.agents.orquestador.agentes.sales.create_accepted_quote",
            return_value=quote,
        ) as persist_quote:
            result = sales_node(state)

        persist_quote.assert_called_once()
        self.assertEqual(result["quote_id"], 27)
        self.assertEqual(result["next_agent"], "payments")

    def test_customer_rejection_does_not_create_quote(self):
        state = {
            "awaiting_input": True,
            "phase": "quote_acceptance",
            "messages": [HumanMessage(content="No")],
            "ticket_id": 91,
            "customer_id": 12,
        }
        with patch("app.agents.orquestador.agentes.sales.cancel_ticket") as cancel, patch(
            "app.agents.orquestador.agentes.sales.create_accepted_quote"
        ) as persist_quote:
            result = sales_node(state)

        cancel.assert_called_once_with(91, 12)
        persist_quote.assert_not_called()
        self.assertTrue(result["ticket_cancelled"])
        self.assertEqual(_supervisor_route(result), "__end__")


if __name__ == "__main__":
    unittest.main()

