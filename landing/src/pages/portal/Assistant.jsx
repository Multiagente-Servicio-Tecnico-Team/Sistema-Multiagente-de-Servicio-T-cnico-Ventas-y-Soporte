import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Archive, Bot, Brain, CircleCheck, Clock, Cpu, Info, PhoneCall, ReceiptText, SendHorizontal, UserRound, Wrench,
} from "lucide-react";
import { formatPEN, useStore } from "../../data/store.jsx";

const TICKET_ID = "TCK-2041";

const suggestions = [
  {
    icon: Archive,
    label: "Consultar estado de stock",
    reply: "La unidad SSD NVMe 1TB Samsung 980 de tu presupuesto está reservada para el ticket #TCK-2041 en el inventario del taller. No se liberará mientras el presupuesto esté vigente.",
  },
  {
    icon: PhoneCall,
    label: "Pedir llamada técnica",
    reply: "Registré tu solicitud de llamada. Un técnico se comunicará al número asociado a tu cuenta dentro del horario de atención del taller.",
  },
  {
    icon: Clock,
    label: "¿Cuánto tardará el respaldo de datos?",
    reply: "El tiempo de respaldo depende del estado real de la unidad. El técnico lo confirmará tras la prueba de lectura; no te daré un plazo sin esa validación.",
  },
];

const FALLBACK =
  "Recibí tu consulta y la añadí al expediente del ticket #TCK-2041. Un especialista la revisará y te responderá por este canal.";

function now() {
  return new Date().toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" });
}

const initialMessages = [
  {
    id: 1,
    from: "user",
    time: "10:41 AM",
    text: "Hola. Mi MacBook Pro 14\" se quedó con pantalla negra tras la última actualización del sistema. Intenté arrancarlo con combinación de teclas de recuperación pero parpadea el LED ámbar y no detecta el disco principal. ¿Tienen repuestos originales para verificar si el SSD murió?",
  },
  {
    id: 2,
    from: "bot",
    time: "10:42 AM",
    paragraphs: [
      "Lamento el inconveniente con tu MacBook Pro 14\". La secuencia de parpadeo ámbar combinada con la falta de montaje del volumen raíz indica una falla crítica en el módulo de estado sólido posterior al ciclo de escritura del firmware.",
      "He verificado nuestro inventario local en taller. Disponemos de unidad NVMe de alto rendimiento certificada con disipación térmica activa. A continuación te presento la cotización oficial pre-aprobada por el sistema de gestión:",
    ],
    budget: true,
  },
];

function BudgetCard({ ticket, onApprove }) {
  const approved = ticket.status !== "approval";
  const icons = [Wrench, Cpu];
  return (
    <div className="quote">
      <div className="quote__head">
        <span className="icon-tile icon-tile--solid icon-tile--sm"><ReceiptText size={18} aria-hidden="true" /></span>
        <div>
          <strong>Tarjeta de Presupuesto Técnico Detallada</strong>
          <p className="mono-small">Cotización instantánea vinculada a inventario físico</p>
        </div>
      </div>
      <div className="quote__body">
        {ticket.lines.map((l, i) => {
          const Icon = icons[i] || Cpu;
          return (
            <div key={l.label} className="quote__line">
              <Icon size={18} aria-hidden="true" />
              <span>{l.label}</span>
              <span className="mono">{formatPEN(l.amount)}</span>
            </div>
          );
        })}
        <div className="quote__total">
          <div className="quote__sub"><span>Subtotal bruto:</span><span>{formatPEN(ticket.total)} PEN</span></div>
          <div className="quote__sum"><strong>Total Calculado:</strong><span>{formatPEN(ticket.total)}<small> PEN</small></span></div>
        </div>
        <button type="button" className={`btn btn--block btn--lg ${approved ? "btn--done" : "btn--primary"}`} onClick={onApprove} disabled={approved}>
          <CircleCheck size={18} aria-hidden="true" />
          {approved ? "Presupuesto aprobado · reparación autorizada" : "Aceptar Presupuesto y Autorizar Reparación"}
        </button>
      </div>
    </div>
  );
}

export default function Assistant() {
  const { clientTickets, dispatch } = useStore();
  const ticket = clientTickets.find((t) => t.id === TICKET_ID);
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [typing, setTyping] = useState(false);
  const endRef = useRef(null);
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [messages, typing]);

  const reply = (text) => {
    setTyping(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setTyping(false);
      setMessages((m) => [...m, { id: Date.now() + 1, from: "bot", time: now(), paragraphs: [text] }]);
    }, 700);
  };

  const send = (text, answer = FALLBACK) => {
    const clean = text.trim();
    if (!clean) return;
    setMessages((m) => [...m, { id: Date.now(), from: "user", time: now(), text: clean }]);
    setDraft("");
    reply(answer);
  };

  const approve = () => {
    dispatch({ type: "approveBudget", id: TICKET_ID });
    reply("Listo. Registré tu aprobación con fecha y hora, y el taller ya inició la reparación. Puedes seguir el avance en Mis Tickets.");
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(draft);
    }
  };

  return (
    <div className="container-chat">
      <div className="chat-title">
        <h1>Diagnóstico Asistido y Cotización Inteligente</h1>
        <span className="pill pill--green"><span className="pill__dot" />En línea</span>
      </div>

      <section className="copilot" aria-label="Conversación con TechFix Copilot">
        <header className="copilot__head">
          <span className="copilot__avatar"><Bot size={22} aria-hidden="true" /></span>
          <div>
            <h2>TechFix Copilot</h2>
            <p>Especialista en Diagnóstico y Presupuestos de Hardware · Ticket #{TICKET_ID}</p>
          </div>
        </header>

        <div className="copilot__log" aria-live="polite">
          {messages.map((m) =>
            m.from === "user" ? (
              <div key={m.id} className="msg msg--user">
                <div className="msg__content">
                  <p className="msg__meta">Tú (Cliente) <time>{m.time}</time></p>
                  <p className="msg__bubble">{m.text}</p>
                </div>
                <span className="msg__avatar msg__avatar--user"><UserRound size={16} aria-hidden="true" /></span>
              </div>
            ) : (
              <div key={m.id} className="msg msg--bot">
                <span className="msg__avatar"><Brain size={16} aria-hidden="true" /></span>
                <div className="msg__content">
                  <p className="msg__meta"><strong>Agente Diagnóstico IA</strong> <time>{m.time}</time></p>
                  <div className="msg__bubble">
                    {m.paragraphs.map((p) => <p key={p}>{p}</p>)}
                  </div>
                  {m.budget && ticket && <BudgetCard ticket={ticket} onApprove={approve} />}
                </div>
              </div>
            )
          )}
          {typing && (
            <div className="msg msg--bot">
              <span className="msg__avatar"><Brain size={16} aria-hidden="true" /></span>
              <div className="typing" aria-label="El agente está escribiendo"><span /><span /><span /></div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <footer className="copilot__composer">
          <div className="quick">
            <span className="mono-label">Sugerencias rápidas:</span>
            {suggestions.map(({ icon: Icon, label, reply: answer }) => (
              <button key={label} type="button" className="quick__btn" onClick={() => send(label, answer)}>
                <Icon size={15} aria-hidden="true" /> {label}
              </button>
            ))}
          </div>
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              send(draft);
            }}
          >
            <textarea
              rows={1}
              className="composer__input"
              placeholder="Escribe tu consulta sobre la reparación o consulta detalles del presupuesto..."
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKey}
              aria-label="Mensaje"
            />
            <button type="submit" className="btn btn--primary" disabled={!draft.trim()}>
              Enviar <SendHorizontal size={16} aria-hidden="true" />
            </button>
          </form>
          <p className="mono-small composer__hint">
            Presiona Shift + Enter para salto de línea · <Info size={12} aria-hidden="true" /> Respuestas de demostración.{" "}
            <Link to="/portal/tickets" className="link">Ver mis tickets</Link>
          </p>
        </footer>
      </section>
    </div>
  );
}
