import json
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage

from app.agents.jerarquico.graph.state import ServiceState
from app.agents.jerarquico.tools.database import make_warranty_lookup_tool
from app.agents.jerarquico.trace import traced_tool
from app.database.repository import ServiceRepository


def make_warranty_agent(repository: ServiceRepository):
    lookup_tool = make_warranty_lookup_tool(repository)

    def warranty_agent(state: ServiceState) -> dict[str, Any]:
        code = state.get("warranty_code", "").strip()
        if not code:
            return {
                "outcome": "warranty_code_required",
                "messages": [
                    AIMessage(content="Indícame el código exacto de la póliza de garantía.")
                ],
            }
        warranty_json = traced_tool(
            state,
            "warranty_lookup",
            lambda: lookup_tool.invoke({"warranty_code": code}),
        )
        warranty = json.loads(warranty_json)
        if not warranty:
            return {
                "warranty_status": "NOT_FOUND",
                "outcome": "warranty_not_found",
                "messages": [
                    AIMessage(
                        content=(
                            "No encontré una póliza con ese código. Verifica el "
                            "código de tu comprobante; no hice cambios en la base."
                        )
                    )
                ],
            }
        if int(warranty["customer_id"]) != state["customer_id"]:
            return {
                "warranty_status": "NOT_FOUND",
                "outcome": "warranty_not_found",
                "messages": [
                    AIMessage(
                        content=(
                            "No encontré una póliza asociada a tu cuenta con ese "
                            "código. Verifícalo en tu comprobante."
                        )
                    )
                ],
            }

        status = str(warranty["status"])
        end_date = warranty["end_date"]
        end_date_text = (
            end_date.isoformat()
            if hasattr(end_date, "isoformat")
            else str(end_date)[:10]
        )
        is_active = status == "ACTIVE" and warranty["not_expired"]
        if state.get("request_type") != "WARRANTY_CLAIM":
            status_text = "vigente" if is_active else "no vigente"
            return {
                "warranty_id": int(warranty["id"]),
                "warranty_status": status,
                "outcome": "warranty_status_checked",
                "messages": [
                    AIMessage(
                        content=(
                            f"La póliza {warranty['warranty_code']} figura como "
                            f"{status_text} para {warranty['item_or_service_name']}. "
                            f"Vence el {end_date_text}. "
                            f"Estado registrado: {status}."
                        )
                    )
                ],
            }

        if not is_active:
            return {
                "warranty_id": int(warranty["id"]),
                "warranty_status": status,
                "outcome": "warranty_not_covered",
                "messages": [
                    AIMessage(
                        content=(
                            f"La póliza {warranty['warranty_code']} no aparece "
                            f"vigente (estado registrado: {status}; vencimiento: "
                            f"{end_date_text}). No registré un reclamo. "
                            "Si deseas una evaluación de reparación pagada, dímelo "
                            "y te orientaré por ese flujo."
                        )
                    )
                ],
            }

        claim_code = f"CLM-{uuid4().hex[:12].upper()}"
        traced_tool(
            state,
            "warranty_claim_write",
            lambda: repository.create_warranty_claim(
                warranty_id=int(warranty["id"]),
                ticket_id=state["ticket_id"],
                customer_id=state["customer_id"],
                claim_code=claim_code,
                reason=state["failure_description"],
            ),
        )
        return {
            "warranty_id": int(warranty["id"]),
            "warranty_status": status,
            "warranty_claim_code": claim_code,
            "ticket_status": "WARRANTY_IN_REVIEW",
            "awaiting_logistics": True,
            "outcome": "warranty_claim_registered",
            "messages": [
                AIMessage(
                    content=(
                        f"Registré el reclamo {claim_code} en estado de revisión. "
                        "La cobertura final requiere evaluación del equipo. Para "
                        "coordinar su recepción, indica si lo llevarás presencialmente "
                        "o lo enviarás por courier."
                    )
                )
            ],
        }

    return warranty_agent
