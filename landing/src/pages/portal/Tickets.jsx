import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CircleCheck, Plus, Search, Store } from "lucide-react";
import { ItemIcon } from "../../components/ui.jsx";
import { formatPEN, parseMoney } from "../../data/store.jsx";
import { chatApi } from "../../api/chat.js";

const statusInfo = {
  NEW: { id: "received", label: "Recibido · En triage", tone: "blue" },
  IN_DIAGNOSIS: { id: "workshop", label: "En diagnóstico / taller", tone: "blue" },
  QUOTED: { id: "approval", label: "Presupuesto enviado", tone: "teal" },
  PAYMENT_PENDING: { id: "payment", label: "Pago pendiente", tone: "teal" },
  PAID: { id: "workshop", label: "Pago registrado", tone: "blue" },
  IN_REPAIR: { id: "workshop", label: "En reparación / taller", tone: "blue" },
  READY_FOR_DELIVERY: { id: "ready", label: "Listo para retiro o despacho", tone: "green" },
  DELIVERED: { id: "done", label: "Entregado", tone: "muted" },
  CANCELLED: { id: "done", label: "Cancelado", tone: "muted" },
  WARRANTY_IN_REVIEW: { id: "workshop", label: "Garantía en revisión", tone: "blue" },
};

const requestLabels = {
  REPAIR: "Reparación",
  SUPPORT: "Soporte técnico",
  SALE: "Venta de productos",
  PC_BUILD: "Armado de PC",
  WARRANTY_CLAIM: "Reclamo de garantía",
};

const filters = [
  { id: "all", label: "Todos", match: () => true },
  { id: "process", label: "En Proceso", match: (t) => ["received", "workshop", "approval", "payment"].includes(t.status) },
  { id: "ready", label: "Listo para Retiro", match: (t) => t.status === "ready" },
  { id: "done", label: "Finalizado", match: (t) => t.status === "done" },
];

function cardFromTicket(ticket) {
  const state = statusInfo[ticket.status] || statusInfo.NEW;
  const quote = ticket.quote;
  const lines = quote ? [
    { label: "Mano de obra", amount: parseMoney(quote.labor_cost) },
    ...quote.lines.map((line) => ({
      label: `${line.name}${line.quantity > 1 ? ` × ${line.quantity}` : ""}`,
      amount: parseMoney(line.subtotal),
    })),
  ].filter((line) => line.amount !== null && line.amount > 0) : [];
  const date = ticket.created_at ? new Date(ticket.created_at) : null;
  return {
    id: ticket.code,
    when: date && !Number.isNaN(date.valueOf())
      ? date.toLocaleString("es-PE", { dateStyle: "medium", timeStyle: "short" })
      : "Fecha no disponible",
    kind: requestLabels[ticket.request_type] || "Consulta",
    device: ticket.title,
    icon: ticket.request_type === "PC_BUILD" ? "monitor" : "laptop",
    summary: ticket.failure_description,
    note: ticket.status === "QUOTED" ? "Tienes una cotización disponible." : "",
    status: state.id,
    statusLabel: state.label,
    tone: state.tone,
    lines,
    total: quote ? parseMoney(quote.total_amount) : null,
  };
}

export default function Tickets() {
  const [tickets, setTickets] = useState([]);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTickets = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await chatApi.listMyTickets();
      setTickets(data.map(cardFromTicket));
    } catch (err) {
      setError(err?.message || "No se pudieron cargar tus tickets.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTickets(); }, []);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const f = filters.find((x) => x.id === filter);
    return tickets.filter((t) => f.match(t) && (!q || `${t.id} ${t.device} ${t.summary}`.toLowerCase().includes(q)));
  }, [tickets, filter, query]);

  return (
    <div className="container-narrow">
      <div className="page-head">
        <h1 className="page-title">Mis Tickets de Atención</h1>
        <Link to="/portal/asistente" className="btn btn--primary">
          <Plus size={18} aria-hidden="true" /> Nueva Consulta / Chat IA
        </Link>
      </div>

      <div className="toolbar">
        <label className="search">
          <Search size={18} aria-hidden="true" />
          <input type="search" placeholder="Buscar por código o equipo..." value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Buscar tickets" />
        </label>
        <div className="chips" role="tablist" aria-label="Filtrar por estado">
          {filters.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={filter === f.id}
              className={`chip${filter === f.id ? " is-active" : ""}`}
              onClick={() => setFilter(f.id)}
            >
              {f.label} ({tickets.filter(f.match).length})
            </button>
          ))}
        </div>
      </div>

      <div className="ticket-list" aria-busy={loading}>
        {loading && <p className="empty">Cargando tus tickets...</p>}
        {!loading && error && (
          <div className="empty-panel">
            <p role="alert">{error}</p>
            <button type="button" className="btn btn--ghost btn--sm" onClick={loadTickets}>Reintentar</button>
          </div>
        )}
        {!loading && !error && visible.length === 0 && (
          <p className="empty">{tickets.length ? "No hay tickets que coincidan con la búsqueda." : "Todavía no tienes tickets. Inicia una consulta en el chat para crear uno."}</p>
        )}
        {!loading && !error && visible.map((t) => (
          <article key={t.id} className={`tcard${t.status === "done" ? " tcard--muted" : ""}`}>
            <div className="tcard__meta">
              <span className="tcard__id">#{t.id}</span>
              <span className="tcard__when">{t.when}</span>
              <span className="tag">{t.kind}</span>
              <span className={`pill pill--${t.tone} tcard__status`}>
                {t.status === "done" ? <CircleCheck size={13} aria-hidden="true" /> : <span className="pill__dot" />}
                {t.statusLabel}
              </span>
            </div>
            <div className="tcard__body">
              <span className="tcard__icon"><ItemIcon name={t.icon} /></span>
              <div className="tcard__text">
                <h2>{t.device}</h2>
                <p>{t.summary}</p>
                {t.note && <p className="mono-small">{t.note}</p>}
                {t.status === "ready" && <span className="pickup"><Store size={14} aria-hidden="true" /> Disponible para retiro o despacho</span>}
              </div>
              {t.total !== null && <div className="tcard__amount"><span className="mono-label">Total cotizado</span><strong>{formatPEN(t.total)}</strong></div>}
            </div>
            {t.lines.length > 0 && (
              <div className="budget">
                {t.lines.map((line) => (
                  <div key={line.label} className="budget__row"><span>{line.label}</span><span className="mono">{formatPEN(line.amount)}</span></div>
                ))}
                <div className="budget__row budget__row--total"><span>Total</span><span className="mono">{formatPEN(t.total)}</span></div>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
