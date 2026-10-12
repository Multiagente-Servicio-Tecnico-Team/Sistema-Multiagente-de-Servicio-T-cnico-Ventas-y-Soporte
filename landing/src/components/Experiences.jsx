import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Wrench, Smartphone, Bot, CircleCheck } from "lucide-react";
import Eyebrow from "./Eyebrow.jsx";

const queue = [
  { id: "#TCK-2041", device: "MacBook Pro 14”", status: "Diagnóstico", tone: "blue" },
  { id: "#TCK-2040", device: "iPhone 15 Pro Max", status: "Espera stock", tone: "cyan" },
  { id: "#TCK-2038", device: "Dell XPS 15", status: "Listo retiro", tone: "green" },
];

const workshopPoints = [
  "Carga de trabajo y SLA siempre visibles",
  "Reservas de piezas vinculadas al ticket",
  "Excepciones destacadas antes del retraso",
];

const clientPoints = [
  "Presupuesto explicado, no solo enviado",
  "Aprobación digital con registro de hora",
  "Seguimiento 24/7 desde cualquier dispositivo",
];

function Checks({ items }) {
  return (
    <ul className="checklist checklist--circle">
      {items.map((it) => (
        <li key={it}><CircleCheck size={16} aria-hidden="true" />{it}</li>
      ))}
    </ul>
  );
}

export default function Experiences() {
  const [approved, setApproved] = useState(false);

  return (
    <section className="section">
      <div className="container">
        <Eyebrow>Dos experiencias, un mismo expediente</Eyebrow>
        <h2 className="h2 h2--narrow">Claridad para el taller. Confianza para el cliente.</h2>
        <p className="lead lead--wide">
          El equipo operativo gana una vista accionable de cada caso, mientras el cliente recibe
          información concreta, aprueba presupuestos y consulta avances sin perseguir respuestas.
        </p>

        <div className="exp">
          <article className="exp__panel">
            <div className="exp__head">
              <div>
                <p className="mono-label mono-label--blue">Para el taller</p>
                <h3>Priorizar, resolver y anticipar</h3>
              </div>
              <span className="icon-tile icon-tile--solid"><Wrench size={20} aria-hidden="true" /></span>
            </div>
            <div className="queue">
              <div className="queue__head">
                <span>Cola inteligente de hoy</span>
                <span className="mono-label">24 tickets activos</span>
              </div>
              {queue.map((t) => (
                <div key={t.id} className="queue__row">
                  <span className="queue__id">{t.id}</span>
                  <span className="queue__device">{t.device}</span>
                  <span className={`pill pill--${t.tone}`}><span className="pill__dot" />{t.status}</span>
                </div>
              ))}
            </div>
            <Checks items={workshopPoints} />
            <Link to="/taller" className="exp__link">Ir al panel del taller <ArrowRight size={16} aria-hidden="true" /></Link>
          </article>

          <article className="exp__panel">
            <div className="exp__head">
              <div>
                <p className="mono-label mono-label--blue">Para el cliente</p>
                <h3>Entender, aprobar y seguir</h3>
              </div>
              <span className="icon-tile icon-tile--solid"><Smartphone size={20} aria-hidden="true" /></span>
            </div>
            <div className="chat">
              <p className="chat__user">¿Ya confirmaron si el SSD necesita reemplazo?</p>
              <div className="chat__bot">
                <span className="chat__avatar"><Bot size={16} aria-hidden="true" /></span>
                <div className="chat__bubble">
                  <p>
                    Sí. El diagnóstico fue validado y reservamos una unidad compatible. La
                    cotización está lista para tu aprobación.
                  </p>
                  <div className="chat__total">
                    <span>Total calculado</span>
                    <strong>S/. 395.00</strong>
                  </div>
                </div>
              </div>
              <button
                type="button"
                className={`chat__approve${approved ? " is-approved" : ""}`}
                onClick={() => setApproved(true)}
                disabled={approved}
              >
                {approved ? (
                  <><CircleCheck size={18} aria-hidden="true" /> Presupuesto aprobado · reparación autorizada</>
                ) : (
                  "Aprobar presupuesto y autorizar reparación"
                )}
              </button>
            </div>
            <Checks items={clientPoints} />
            <Link to="/portal/tickets" className="exp__link">Ir al portal del cliente <ArrowRight size={16} aria-hidden="true" /></Link>
          </article>
        </div>
      </div>
    </section>
  );
}
