import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, CircleCheck, ClipboardCheck, Eye, Mail, PlusCircle, Search, SlidersHorizontal, Ticket, Upload, UserRound } from "lucide-react";
import { Pagination } from "../../components/ui.jsx";
import { centsToInput, formatPEN, STAFF_STATUSES, TICKET_CATEGORIES, useStore } from "../../data/store.jsx";

const PAGE_SIZE = 5;
const categoryTone = { "Reparación": "blue", Venta: "cyan", Soporte: "muted" };

function exportCsv(rows) {
  const header = ["ID", "Fecha", "Cliente", "Teléfono", "Dispositivo", "Detalle", "Categoría", "Presupuesto (PEN)", "Estado", "Origen"];
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = rows.map((t) => [t.id, t.date, t.client, t.phone, t.device, t.issue, t.category, centsToInput(t.budget), t.status, t.origin].map(esc).join(","));
  const blob = new Blob([`﻿${[header.map(esc).join(","), ...lines].join("\r\n")}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "reporte-tickets-techfix.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function Workshop() {
  const { staffTickets, dispatch } = useStore();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("Todos");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const stats = useMemo(() => ({
    active: staffTickets.filter((t) => t.status !== "Entregado").length,
    waiting: staffTickets.filter((t) => t.status === "Esperando Stock").length,
    ready: staffTickets.filter((t) => t.status === "Listo para Retiro").length,
    fresh: staffTickets.filter((t) => t.status === "Nuevo").length,
  }), [staffTickets]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return staffTickets.filter((t) =>
      (category === "Todos" || t.category === category) &&
      (!status || t.status === status) &&
      (!q || `${t.id} ${t.client} ${t.device} ${t.issue}`.toLowerCase().includes(q))
    );
  }, [staffTickets, query, category, status]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const rows = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const from = filtered.length ? (current - 1) * PAGE_SIZE + 1 : 0;

  const resetPage = (fn) => (value) => {
    fn(value);
    setPage(1);
  };

  return (
    <div className="staff-page">
      <div className="page-head">
        <div>
          <span className="live-dot" aria-hidden="true" />
          <h1 className="page-title">Gestión Integral de Taller</h1>
        </div>
        <div className="page-head__actions">
          <button type="button" className="btn btn--soft" onClick={() => exportCsv(filtered)}>
            <Upload size={17} aria-hidden="true" /> Exportar Reporte
          </button>
          <Link to="/taller/tickets/nuevo" className="btn btn--primary">
            <PlusCircle size={17} aria-hidden="true" /> Nuevo Ticket Manual
          </Link>
        </div>
      </div>

      <div className="kpis">
        <div className="kpi kpi--blue">
          <div>
            <p className="mono-label">Tickets activos</p>
            <p className="kpi__value">{String(stats.active).padStart(2, "0")} <span className="kpi__delta">{stats.fresh} nuevos</span></p>
            <p className="kpi__note">Sin entregar al cliente</p>
          </div>
          <span className="icon-tile"><Ticket size={22} aria-hidden="true" /></span>
        </div>
        <div className="kpi kpi--gray">
          <div>
            <p className="mono-label">Esperando repuestos</p>
            <p className="kpi__value">{String(stats.waiting).padStart(2, "0")}</p>
            <p className="kpi__note"><Link to="/taller/inventario" className="link">Revisar stock crítico</Link></p>
          </div>
          <span className="icon-tile"><ClipboardCheck size={22} aria-hidden="true" /></span>
        </div>
        <div className="kpi kpi--light">
          <div>
            <p className="mono-label">Listos para retiro</p>
            <p className="kpi__value">{String(stats.ready).padStart(2, "0")}</p>
            <p className="kpi__note">Aviso al cliente enviado</p>
          </div>
          <span className="icon-tile"><CircleCheck size={22} aria-hidden="true" /></span>
        </div>
      </div>

      <div className="toolbar toolbar--wrap">
        <label className="search search--grow">
          <Search size={18} aria-hidden="true" />
          <input
            type="search"
            placeholder="Buscar por cliente, dispositivo o ID de ticket"
            value={query}
            onChange={(e) => resetPage(setQuery)(e.target.value)}
            aria-label="Buscar tickets"
          />
        </label>
        <div className="segmented" role="tablist" aria-label="Categoría">
          {["Todos", ...TICKET_CATEGORIES].map((c) => (
            <button key={c} type="button" role="tab" aria-selected={category === c} className={category === c ? "is-active" : ""} onClick={() => resetPage(setCategory)(c)}>
              {c}
            </button>
          ))}
        </div>
        <label className="select-chip">
          <SlidersHorizontal size={16} aria-hidden="true" />
          <select value={status} onChange={(e) => resetPage(setStatus)(e.target.value)} aria-label="Filtrar por estado">
            <option value="">Cualquier Estado</option>
            {STAFF_STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
      </div>

      <div className="table-card">
        <table className="rtable">
          <thead>
            <tr>
              <th>ID Ticket</th>
              <th>Cliente</th>
              <th>Dispositivo / Modelo</th>
              <th>Categoría</th>
              <th>Presupuesto</th>
              <th>Estado del flujo</th>
              <th>Origen</th>
              <th className="ta-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={8} className="empty">No hay tickets con estos filtros.</td></tr>
            )}
            {rows.map((t) => (
              <tr key={t.id}>
                <td data-label="ID Ticket">
                  <Link to={`/taller/tickets/${t.id}`} className="rtable__id">#{t.id}</Link>
                  <span className="rtable__date">{t.date}</span>
                </td>
                <td data-label="Cliente">
                  <strong className="rtable__strong">{t.client}</strong>
                  <span className="mono-small">{t.phone}</span>
                </td>
                <td data-label="Dispositivo">
                  <strong className="rtable__strong">{t.device}</strong>
                  <span className="rtable__sub">{t.issue}</span>
                </td>
                <td data-label="Categoría"><span className={`tag tag--${categoryTone[t.category]}`}>{t.category}</span></td>
                <td data-label="Presupuesto" className="mono nowrap">{formatPEN(t.budget)}</td>
                <td data-label="Estado">
                  <select
                    className="status-select"
                    value={t.status}
                    onChange={(e) => dispatch({ type: "updateTicket", id: t.id, changes: { status: e.target.value } })}
                    aria-label={`Estado de ${t.id}`}
                  >
                    {STAFF_STATUSES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </td>
                <td data-label="Origen">
                  <span className={`origin origin--${t.origin === "Bot" ? "bot" : "desk"}`}>
                    <span className="origin__icon">{t.origin === "Bot" ? <Bot size={13} /> : <UserRound size={13} />}</span>
                    {t.origin}
                  </span>
                </td>
                <td data-label="Acciones" className="ta-right">
                  <div className="row-actions">
                    <Link to={`/taller/tickets/${t.id}`} className="icon-btn icon-btn--soft" aria-label={`Ver ${t.id}`}><Eye size={17} /></Link>
                    {t.email ? (
                      <a href={`mailto:${t.email}?subject=${encodeURIComponent(`Ticket #${t.id}`)}`} className="icon-btn icon-btn--soft" aria-label={`Escribir a ${t.client}`}><Mail size={17} /></a>
                    ) : (
                      <span className="icon-btn icon-btn--soft is-disabled" title="Sin correo registrado" aria-label="Sin correo registrado"><Mail size={17} /></span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="table-card__foot">
          <Pagination
            page={current}
            pages={pages}
            onChange={setPage}
            label={`Mostrando ${from}-${from + rows.length - (rows.length ? 1 : 0)} de ${filtered.length} tickets`}
          />
        </div>
      </div>
    </div>
  );
}
