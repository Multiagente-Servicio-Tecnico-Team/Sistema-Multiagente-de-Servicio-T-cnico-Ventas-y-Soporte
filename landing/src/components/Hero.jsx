import { Link } from "react-router-dom";
import { Play, Layers, CircleCheck, ShieldCheck, Workflow } from "lucide-react";
import Eyebrow from "./Eyebrow.jsx";
import Dashboard from "./Dashboard.jsx";

const trust = [
  { icon: CircleCheck, label: "Implementación guiada" },
  { icon: ShieldCheck, label: "Datos bajo control" },
  { icon: Workflow, label: "Integración operativa" },
];

const integrations = ["WhatsApp Business", "Correo transaccional", "Catálogos de repuestos", "ERP y facturación"];

export default function Hero() {
  return (
    <section className="hero" id="inicio">
      <div className="container hero__content">
        <Eyebrow center>Sistema multiagente para servicio técnico</Eyebrow>
        <h1 className="hero__title">
          Cada reparación avanza <br className="hide-sm" />
          con inteligencia coordinada
        </h1>
        <p className="hero__lead">
          TechFix.AI conecta diagnóstico, triage, inventario y comunicación en un solo flujo.
          Agentes especializados colaboran para resolver más rápido, cotizar con precisión y
          mantener a cada cliente informado.
        </p>
        <div className="hero__ctas">
          <Link to="/portal/asistente" className="btn btn--primary btn--lg">
            <Play size={18} aria-hidden="true" /> Ver TechFix.AI en acción
          </Link>
          <a href="#agentes" className="btn btn--ghost btn--lg">
            <Layers size={18} aria-hidden="true" /> Explorar capacidades
          </a>
        </div>
        <ul className="hero__trust">
          {trust.map(({ icon: Icon, label }) => (
            <li key={label}>
              <Icon size={16} aria-hidden="true" /> {label}
            </li>
          ))}
        </ul>
      </div>

      <div className="container hero__dashboard" id="plataforma">
        <Dashboard />
      </div>

      <div className="integrations">
        <div className="container integrations__inner">
          <span className="integrations__label">Operación conectada con</span>
          {integrations.map((name) => (
            <span key={name} className="integrations__item">{name}</span>
          ))}
        </div>
      </div>
    </section>
  );
}
