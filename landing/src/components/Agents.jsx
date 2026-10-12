import { Brain, Waypoints, Warehouse, MessagesSquare, Check } from "lucide-react";
import Eyebrow from "./Eyebrow.jsx";

const agents = [
  { icon: Brain, name: "Agente Diagnóstico", chain: ["Evidencia", "Hipótesis", "Cotización"], items: ["Interpreta síntomas y antecedentes", "Sugiere pruebas y nivel técnico", "Genera presupuesto trazable"] },
  { icon: Waypoints, name: "Agente Triage", chain: ["Entrada", "Prioridad", "Responsable"], items: ["Clasifica tipo y urgencia", "Aplica SLA y reglas del taller", "Escala excepciones críticas"] },
  { icon: Warehouse, name: "Agente Inventario", chain: ["Demanda", "Stock", "Reserva"], items: ["Valida compatibilidad de repuestos", "Reserva unidades por ticket", "Anticipa quiebres de stock"] },
  { icon: MessagesSquare, name: "Agente Seguimiento", chain: ["Evento", "Mensaje", "Respuesta"], items: ["Explica estados con lenguaje claro", "Solicita y registra aprobaciones", "Coordina retiro y postservicio"] },
];

export default function Agents() {
  return (
    <section className="section section--tint section--flush-top" id="agentes">
      <div className="container">
        <div className="split-head">
          <div>
            <Eyebrow dot={false}>Especialización que escala</Eyebrow>
            <h2 className="h2">Cada agente domina una decisión crítica</h2>
          </div>
          <p className="split-head__aside">
            Activa las capacidades que necesita tu operación y conserva reglas específicas por sede,
            categoría o nivel técnico.
          </p>
        </div>
        <div className="agents">
          {agents.map(({ icon: Icon, name, chain, items }) => (
            <article key={name} className="card agent">
              <div className="agent__head">
                <span className="icon-tile icon-tile--solid"><Icon size={22} aria-hidden="true" /></span>
                <div className="agent__title">
                  <h3>{name}</h3>
                  <p className="mono-label">{chain.join(" → ")}</p>
                </div>
                <span className="pill pill--green"><span className="pill__dot" />Activo</span>
              </div>
              <ul className="checklist">
                {items.map((it) => (
                  <li key={it}><Check size={16} aria-hidden="true" />{it}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
