import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Ticket, Package, CircleCheck, MessageCircle, Stethoscope, ListChecks, PackageSearch, MessageSquareText,
} from "lucide-react";
import Logo from "./Logo.jsx";

const views = {
  taller: {
    nav: "Taller y triage",
    to: "/taller",
    icon: Ticket,
    title: "Gestión Integral de Taller",
    stats: [
      { label: "Tickets activos", value: "24", note: "Capacidad al 78%", icon: Ticket },
      { label: "Esperando repuestos", value: "05", note: "Reserva automatizada", icon: Package },
      { label: "Listos para retiro", value: "11", note: "Aviso enviado", icon: CircleCheck },
    ],
  },
  stock: {
    nav: "Stock y repuestos",
    to: "/taller/inventario",
    icon: Package,
    title: "Stock y Repuestos",
    stats: [
      { label: "Reservas activas", value: "17", note: "Vinculadas a tickets", icon: Package },
      { label: "Bajo mínimo", value: "03", note: "Reposición sugerida", icon: PackageSearch },
      { label: "Compatibilidad validada", value: "98%", note: "Últimos 30 días", icon: CircleCheck },
    ],
  },
  portal: {
    nav: "Portal del cliente",
    to: "/portal/tickets",
    icon: MessageCircle,
    title: "Portal del Cliente",
    stats: [
      { label: "Conversaciones abiertas", value: "09", note: "Respuesta media 2 min", icon: MessageCircle },
      { label: "Aprobaciones pendientes", value: "04", note: "Recordatorio programado", icon: ListChecks },
      { label: "Aprobadas hoy", value: "12", note: "Sin llamada telefónica", icon: CircleCheck },
    ],
  },
};

const steps = [
  { icon: Stethoscope, state: "current" },
  { icon: ListChecks, state: "done" },
  { icon: PackageSearch, state: "accent" },
  { icon: MessageSquareText, state: "done" },
];

export default function Dashboard() {
  const [view, setView] = useState("taller");
  const current = views[view];

  return (
    <div className="dash">
      <aside className="dash__side">
        <Logo />
        <ul className="dash__nav">
          {Object.entries(views).map(([key, v]) => {
            const Icon = v.icon;
            return (
              <li key={key}>
                <button
                  type="button"
                  className={`dash__navbtn${view === key ? " is-active" : ""}`}
                  aria-pressed={view === key}
                  onClick={() => setView(key)}
                >
                  <Icon size={17} aria-hidden="true" /> {v.nav}
                </button>
              </li>
            );
          })}
        </ul>
        <div className="dash__status">
          <span className="pill pill--green"><span className="pill__dot" />4 agentes activos</span>
          <p>Sincronización completa · hace 18 s</p>
        </div>
      </aside>

      <div className="dash__main">
        <div className="dash__head">
          <div>
            <h3>{current.title}</h3>
            <p className="mono-label">Operación en tiempo real</p>
          </div>
          <div className="dash__headside">
            <span className="pill pill--green"><span className="pill__dot" />Sistema coordinado</span>
            <Link to={current.to} className="dash__open">
              Abrir {current.nav.toLowerCase()} <ArrowRight size={14} aria-hidden="true" />
            </Link>
          </div>
        </div>

        <div className="dash__stats" key={view}>
          {current.stats.map(({ label, value, note, icon: Icon }) => (
            <div key={label} className="stat">
              <div>
                <p className="mono-label">{label}</p>
                <p className="stat__value">{value}</p>
                <p className="stat__note">{note}</p>
              </div>
              <span className="icon-tile"><Icon size={20} aria-hidden="true" /></span>
            </div>
          ))}
        </div>

        <div className="ticket">
          <div className="ticket__head">
            <span className="ticket__id">#TCK-2041 · MacBook Pro 14”</span>
            <span className="pill pill--blue"><span className="pill__dot" />En diagnóstico</span>
          </div>
          <div className="ticket__steps" aria-hidden="true">
            {steps.map(({ icon: Icon, state }, i) => (
              <div key={i} className="ticket__step">
                <span className={`ticket__node is-${state}`}>
                  <Icon size={18} />
                </span>
                {i < steps.length - 1 && <span className="ticket__line" />}
              </div>
            ))}
          </div>
          <div className="ticket__result">
            <div>
              <strong>Diagnóstico validado · repuesto reservado</strong>
              <p>Cotización S/. 395.00 preparada para aprobación</p>
            </div>
            <CircleCheck size={22} aria-hidden="true" />
          </div>
        </div>
      </div>
    </div>
  );
}
