import { ShieldCheck, KeyRound, History, UserRoundCheck } from "lucide-react";
import Eyebrow from "./Eyebrow.jsx";

const items = [
  { icon: ShieldCheck, title: "Permisos por rol y sede", text: "Cada persona y agente accede solo al contexto necesario para su trabajo." },
  { icon: KeyRound, title: "Datos protegidos", text: "Cifrado en tránsito y reposo, retención configurable y entornos segregados." },
  { icon: History, title: "Bitácora de decisiones", text: "Diagnósticos, cambios de estado, reservas y aprobaciones quedan registrados." },
  { icon: UserRoundCheck, title: "Supervisión humana", text: "Escalamientos y aprobaciones obligatorias según monto, riesgo o excepción." },
];

export default function Security() {
  return (
    <section className="section section--flush-top" id="seguridad">
      <div className="container">
        <div className="security">
          <div className="security__intro">
            <Eyebrow dot={false}>Control empresarial</Eyebrow>
            <h2 className="h3">IA gobernada para una operación confiable</h2>
            <p>Automatiza con límites claros, trazabilidad completa y control humano en decisiones sensibles.</p>
          </div>
          <ul className="security__grid">
            {items.map(({ icon: Icon, title, text }) => (
              <li key={title}>
                <span className="icon-tile"><Icon size={18} aria-hidden="true" /></span>
                <div>
                  <strong>{title}</strong>
                  <p>{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
