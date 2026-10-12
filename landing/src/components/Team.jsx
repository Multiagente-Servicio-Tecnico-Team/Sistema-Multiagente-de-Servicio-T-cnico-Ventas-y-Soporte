import {
  RefreshCw, GitBranch, UserCheck, Stethoscope, Filter, PackageSearch, MessageSquareText, Sparkles,
  Timer, BadgeCheck, BellRing, CircleCheck,
} from "lucide-react";
import Eyebrow from "./Eyebrow.jsx";

const points = [
  { icon: RefreshCw, title: "Contexto compartido, sin duplicar trabajo", text: "El expediente acompaña al ticket de principio a fin." },
  { icon: GitBranch, title: "Decisiones conectadas a datos reales", text: "Precios, stock y tiempos se verifican antes de responder." },
  { icon: UserCheck, title: "Control humano donde importa", text: "Reglas, permisos y escalamiento para cada decisión sensible." },
];

const nodes = [
  { pos: "tl", icon: Stethoscope, title: "Diagnóstico y cotización", text: "Hipótesis, piezas y presupuesto" },
  { pos: "tr", icon: Filter, title: "Triage y tickets", text: "Prioridad, SLA y asignación" },
  { pos: "bl", icon: PackageSearch, title: "Inventario y reserva", text: "Disponibilidad y reposición" },
  { pos: "br", icon: MessageSquareText, title: "Seguimiento al cliente", text: "Estados, aprobaciones y avisos" },
];

const benefits = [
  { icon: Timer, title: "Menos espera entre etapas", text: "El siguiente paso se activa en cuanto existe la información necesaria, sin depender de seguimientos manuales.", tag: "SLA visible en cada transición" },
  { icon: BadgeCheck, title: "Cotizaciones consistentes", text: "Mano de obra, repuestos y disponibilidad se validan antes de presentar una propuesta al cliente.", tag: "Precio y stock trazables" },
  { icon: BellRing, title: "Clientes siempre informados", text: "Cada cambio relevante dispara el mensaje correcto por el canal preferido, con contexto y próximo paso.", tag: "Comunicación proactiva" },
];

export default function Team() {
  return (
    <section className="section team">
      <div className="container">
        <div className="team__grid">
          <div>
            <Eyebrow>Una operación, múltiples especialistas</Eyebrow>
            <h2 className="h2">No es un chatbot. Es un equipo digital coordinado.</h2>
            <p className="lead">
              Cada agente entiende una parte crítica del servicio. El orquestador comparte contexto,
              asigna tareas y valida dependencias para que diagnóstico, stock y comunicación avancen
              como un solo sistema.
            </p>
            <ul className="points">
              {points.map(({ icon: Icon, title, text }) => (
                <li key={title}>
                  <span className="icon-tile icon-tile--sm"><Icon size={17} aria-hidden="true" /></span>
                  <div>
                    <strong>{title}</strong>
                    <p>{text}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="orch" aria-label="Diagrama: el orquestador TechFix coordina cuatro agentes">
            <svg className="orch__lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
              <line x1="50" y1="6" x2="50" y2="94" className="orch__axis" />
              <line x1="8" y1="50" x2="92" y2="50" className="orch__axis" />
              <line x1="30" y1="24" x2="44" y2="44" className="orch__link" />
              <line x1="70" y1="24" x2="56" y2="44" className="orch__link" />
              <line x1="30" y1="76" x2="44" y2="56" className="orch__link" />
              <line x1="70" y1="76" x2="56" y2="56" className="orch__link" />
            </svg>
            {nodes.map(({ pos, icon: Icon, title, text }) => (
              <div key={pos} className={`orch__node orch__node--${pos}`}>
                <span className="orch__icon"><Icon size={18} aria-hidden="true" /></span>
                <div>
                  <strong>{title}</strong>
                  <p>{text}</p>
                </div>
              </div>
            ))}
            <div className="orch__center">
              <div className="orch__hub">
                <span className="orch__hubicon"><Sparkles size={18} aria-hidden="true" /></span>
                <div>
                  <strong>Orquestador TechFix</strong>
                  <p>Coordina contexto, prioridades y reglas</p>
                </div>
              </div>
              <div className="orch__sync">
                <span className="pill pill--green"><span className="pill__dot" />Sincronizado</span>
                <span className="orch__latency">1.8 s</span>
              </div>
            </div>
          </div>
        </div>

        <div className="benefits">
          {benefits.map(({ icon: Icon, title, text, tag }) => (
            <article key={title} className="card benefit">
              <span className="icon-tile"><Icon size={20} aria-hidden="true" /></span>
              <h3>{title}</h3>
              <p>{text}</p>
              <span className="benefit__tag"><CircleCheck size={15} aria-hidden="true" />{tag}</span>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
