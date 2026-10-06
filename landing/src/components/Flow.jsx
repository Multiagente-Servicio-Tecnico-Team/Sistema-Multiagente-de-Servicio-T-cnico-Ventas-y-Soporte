import { MessageCircle, ListTree, ScanSearch, Package, Send } from "lucide-react";
import Eyebrow from "./Eyebrow.jsx";

const steps = [
  { icon: MessageCircle, title: "Ingreso y contexto", text: "Captura equipo, síntoma, urgencia y evidencia desde chat o recepción.", result: "Ticket estructurado" },
  { icon: ListTree, title: "Triage automático", text: "Clasifica, prioriza y asigna SLA según reglas del servicio.", result: "Ruta y responsable" },
  { icon: ScanSearch, title: "Diagnóstico y precio", text: "Propone pruebas, mano de obra y piezas compatibles.", result: "Cotización validada" },
  { icon: Package, title: "Reserva y ejecución", text: "Bloquea stock, activa tareas y mantiene el expediente al día.", result: "Trabajo listo" },
  { icon: Send, title: "Seguimiento y cierre", text: "Solicita aprobación, avisa avances y coordina entrega.", result: "Cliente informado" },
];

export default function Flow() {
  return (
    <section className="section section--tint" id="flujo">
      <div className="container">
        <Eyebrow>Del primer mensaje al cierre</Eyebrow>
        <h2 className="h2 h2--narrow">Un flujo continuo, sin puntos ciegos</h2>
        <p className="lead lead--wide">
          TechFix.AI convierte cada interacción en una acción operativa. El taller conserva el
          control y el cliente ve exactamente qué está ocurriendo.
        </p>
        <ol className="flow">
          {steps.map(({ icon: Icon, title, text, result }, i) => (
            <li key={title} className="card flow__step">
              <div className="flow__top">
                <span className="icon-tile icon-tile--sm"><Icon size={17} aria-hidden="true" /></span>
                <span className="flow__num">{String(i + 1).padStart(2, "0")}</span>
              </div>
              <h3>{title}</h3>
              <p>{text}</p>
              <div className="flow__result">
                <span className="mono-label">Resultado</span>
                <strong>{result}</strong>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
