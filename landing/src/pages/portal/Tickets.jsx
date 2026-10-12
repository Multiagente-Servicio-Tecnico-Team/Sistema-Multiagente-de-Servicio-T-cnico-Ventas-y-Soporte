import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CircleCheck, MessageSquareText, Plus, Search, Store } from "lucide-react";
import { ItemIcon, Toast } from "../../components/ui.jsx";
import { formatPEN, useStore } from "../../data/store.jsx";

const statusInfo = {
  received: { label: "Recibido · En triage", tone: "blue" },
  approval: { label: "Esperando aprobación", tone: "teal" },
  workshop: { label: "En diagnóstico / taller", tone: "blue" },
  ready: { label: "Listo para entrega en tienda", tone: "green" },
  done: { label: "Completado", tone: "muted" },
};

const filters = [
  { id: "all", label: "Todos", match: () => true },
  { id: "process", label: "En Proceso", match: (t) => ["received", "approval", "workshop"].includes(t.status) },
  { id: "ready", label: "Listo para Retiro", match: (t) => t.status === "ready" },
  { id: "done", label: "Finalizado", match: (t) => t.status === "done" },
];

export default function Tickets() {
  const { clientTickets, dispatch } = useStore();
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [toast, setToast] = useState("");

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const f = filters.find((x) => x.id === filter);
    return clientTickets.filter((t) => f.match(t) && (!q || `${t.id} ${t.device}`.toLowerCase().includes(q)));
  }, [clientTickets, filter, query]);

  const approve = (id) => {
    dispatch({ type: "approveBudget", id });
    setToast(`Presupuesto de #${id} aprobado. El taller ya fue notificado.`);
  };

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
              {f.label} ({clientTickets.filter(f.match).length})
            </button>
          ))}
        </div>
      </div>

      <div className="ticket-list">
        {visible.length === 0 && <p className="empty">No hay tickets que coincidan con la búsqueda.</p>}
        {visible.map((t) => {
          const info = statusInfo[t.status];
          return (
            <article key={t.id} className={`tcard${t.status === "done" ? " tcard--muted" : ""}`}>
              <div className="tcard__meta">
                <span className="tcard__id">#{t.id}</span>
                <span className="tcard__when">{t.when}</span>
                <span className="tag">{t.kind}</span>
                <span className={`pill pill--${info.tone} tcard__status`}>
                  {t.status === "done" ? <CircleCheck size={13} aria-hidden="true" /> : <span className="pill__dot" />}
                  {info.label}
                </span>
              </div>

              <div className="tcard__body">
                <span className="tcard__icon"><ItemIcon name={t.icon} /></span>
                <div className="tcard__text">
                  <h2>{t.device}</h2>
                  <p>{t.summary}</p>
                  {t.note && t.status === "approval" && <p className="mono-small">{t.note}</p>}
                  {t.pickup && <span className="pickup"><Store size={14} aria-hidden="true" /> {t.pickup}</span>}
                </div>
                {t.lines.length === 0 && (
                  <div className="tcard__amount">
                    {t.status === "ready" && <span className="mono-label">Total pagado</span>}
                    {t.status === "done" && <span className="mono-label">Importe final</span>}
                    {t.status === "received" && <span className="mono-label">Presupuesto</span>}
                    <strong>{formatPEN(t.total)}</strong>
                  </div>
                )}
              </div>

              {t.lines.length > 0 && (
                <div className="budget">
                  {t.lines.map((l) => (
                    <div key={l.label} className="budget__row"><span>{l.label}</span><span className="mono">{formatPEN(l.amount)}</span></div>
                  ))}
                  <div className="budget__row budget__row--total">
                    <span>{t.status === "approval" ? "Total Presupuesto" : "Total Presupuesto Aprobado"}</span>
                    <span className="mono">{formatPEN(t.total)}</span>
                  </div>
                </div>
              )}

              {t.status === "approval" && (
                <div className="tcard__actions">
                  {t.lines.length > 0 && (
                    <Link to={`/portal/asistente?ticket=${t.id}`} className="btn btn--ghost btn--sm">
                      <MessageSquareText size={16} aria-hidden="true" /> Revisar con el asistente
                    </Link>
                  )}
                  <button type="button" className="btn btn--primary btn--sm" onClick={() => approve(t.id)}>
                    <CircleCheck size={16} aria-hidden="true" /> Aprobar presupuesto
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>
      <Toast message={toast} onDone={() => setToast("")} />
    </div>
  );
}
