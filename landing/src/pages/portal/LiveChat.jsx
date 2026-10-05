import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bot, Brain, CircleCheck, CircleX, Info, ReceiptText, RotateCcw, SendHorizontal, Ticket, TriangleAlert, UserRound } from "lucide-react";
import { formatPEN, parseMoney, useStore } from "../../data/store.jsx";
import { authApi } from "../../api/auth.js";
import { chatApi as defaultChatApi, TICKET_STATUS_LABEL } from "../../api/chat.js";

function now() {
  return new Date().toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" });
}

/** Importe del servidor ("180.00") mostrado sin cálculos en el navegador. */
const money = (amount) => formatPEN(parseMoney(amount));

function QuoteCard({ quote, busy, onAction }) {
  const pending = quote.status === "proposed";
  return (
    <div className="quote">
      <div className="quote__head">
        <span className="icon-tile icon-tile--solid icon-tile--sm"><ReceiptText size={18} aria-hidden="true" /></span>
        <div>
          <strong>Presupuesto propuesto</strong>
          <p className="mono-small">Calculado por el agente de ventas</p>
        </div>
      </div>
      <div className="quote__body">
        {quote.lines.map((line) => (
          <div key={line.label} className="quote__line">
            <ReceiptText size={18} aria-hidden="true" />
            <span>{line.label}</span>
            <span className="mono">{money(line.amount)}</span>
          </div>
        ))}
        <div className="quote__total">
          <div className="quote__sum"><strong>Total:</strong><span>{money(quote.total)}<small> {quote.currency}</small></span></div>
        </div>
        {pending ? (
          <div className="btn-row btn-row--start">
            <button type="button" className="btn btn--primary" disabled={busy} onClick={() => onAction("accept_quote")}>
              <CircleCheck size={18} aria-hidden="true" /> Aceptar presupuesto
            </button>
            <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => onAction("reject_quote")}>
              <CircleX size={18} aria-hidden="true" /> Rechazar
            </button>
          </div>
        ) : (
          <p className={`ok-text${quote.status === "rejected" ? " muted" : ""}`}>
            {{ confirmed: "Presupuesto aceptado · reparación autorizada", rejected: "Presupuesto rechazado" }[quote.status]
              || "Reemplazado por un presupuesto más reciente"}
          </p>
        )}
      </div>
    </div>
  );
}

/** Chat conectado al patrón LangGraph: el cliente se identifica con la sesión del inicio de sesión. */
export default function LiveChat({ api = defaultChatApi }) {
  const { session, logout } = useStore();
  const navigate = useNavigate();
  const firstName = (session?.name || "").split(" ")[0];
  const [messages, setMessages] = useState([{
    id: 0, from: "bot", time: now(),
    text: `Hola${firstName ? `, ${firstName}` : ""}. Cuéntame qué equipo tienes y qué falla presenta.`,
  }]);
  const [conversationId, setConversationId] = useState(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [messages, busy]);

  const call = async (payload) => {
    setBusy(true);
    setError(null);
    try {
      const data = await api.sendMessage({ conversationId, ...payload });
      setConversationId(data.conversation_id);
      setMessages((m) => [...m, { id: Date.now() + 1, from: "bot", time: now(), text: data.reply, quote: data.quote, ticket: data.ticket }]);
    } catch (err) {
      if (err?.code === "session_required") {
        // La sesión del servidor terminó: se cierra la local y se vuelve al chat después de ingresar.
        await authApi.logout?.();
        logout();
        navigate("/portal/acceso", { replace: true, state: { from: "/portal/asistente" } });
        return;
      }
      if (err?.code === "not_found") setConversationId(null);
      setError({ message: err?.message, payload });
    } finally {
      setBusy(false);
    }
  };

  const send = (e) => {
    e?.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setMessages((m) => [...m, { id: Date.now(), from: "user", time: now(), text }]);
    setDraft("");
    call({ message: text });
  };

  // Solo la última tarjeta de presupuesto reacciona a los botones.
  const lastQuoteId = [...messages].reverse().find((m) => m.quote)?.id;

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
            <p>Agentes de atención, soporte técnico y ventas · Sesión de {session?.email}</p>
          </div>
        </header>

        <div className="copilot__log" aria-live="polite">
          {messages.map((m) =>
            m.from === "user" ? (
              <div key={m.id} className="msg msg--user">
                <div className="msg__content">
                  <p className="msg__meta">Tú <time>{m.time}</time></p>
                  <p className="msg__bubble">{m.text}</p>
                </div>
                <span className="msg__avatar msg__avatar--user"><UserRound size={16} aria-hidden="true" /></span>
              </div>
            ) : (
              <div key={m.id} className="msg msg--bot">
                <span className="msg__avatar"><Brain size={16} aria-hidden="true" /></span>
                <div className="msg__content">
                  <p className="msg__meta"><strong>Agente TechFix</strong> <time>{m.time}</time></p>
                  <div className="msg__bubble"><p>{m.text}</p></div>
                  {m.quote && (
                    <QuoteCard
                      quote={m.id === lastQuoteId ? m.quote : { ...m.quote, status: m.quote.status === "proposed" ? "superseded" : m.quote.status }}
                      busy={busy || m.id !== lastQuoteId}
                      onAction={(action) => call({ action })}
                    />
                  )}
                  {m.ticket && (
                    <div className="created">
                      <span className="icon-tile icon-tile--sm"><Ticket size={18} aria-hidden="true" /></span>
                      <div>
                        <strong>Ticket {m.ticket.code}</strong>
                        <p>Estado: {TICKET_STATUS_LABEL[m.ticket.status] || m.ticket.status}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )
          )}
          {busy && (
            <div className="msg msg--bot">
              <span className="msg__avatar"><Brain size={16} aria-hidden="true" /></span>
              <div className="typing" aria-label="El agente está escribiendo"><span /><span /><span /></div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <footer className="copilot__composer">
          {error && (
            <div className="form-alert" role="alert">
              <TriangleAlert size={16} aria-hidden="true" />
              <span>{error.message}</span>
              {error.payload && (
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => call(error.payload)}>
                  <RotateCcw size={14} aria-hidden="true" /> Reintentar
                </button>
              )}
            </div>
          )}
          <form className="composer" onSubmit={send}>
            <textarea
              rows={1}
              className="composer__input"
              placeholder="Ej.: Mi laptop HP no detecta el disco desde ayer"
              value={draft}
              maxLength={2000}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) send(e); }}
              aria-label="Mensaje"
            />
            <button type="submit" className="btn btn--primary" disabled={!draft.trim() || busy}>
              Enviar <SendHorizontal size={16} aria-hidden="true" />
            </button>
          </form>
          <p className="mono-small composer__hint">
            Presiona Shift + Enter para salto de línea · <Info size={12} aria-hidden="true" /> No compartas contraseñas en el chat.{" "}
            <Link to="/portal/tickets" className="link">Ver mis tickets</Link>
          </p>
        </footer>
      </section>
    </div>
  );
}
