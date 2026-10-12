import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpDown, ClipboardCheck, Laptop, Pencil, PlusCircle, Search, SlidersHorizontal, TriangleAlert } from "lucide-react";
import { ItemIcon, Pagination } from "../../components/ui.jsx";
import { formatPEN, PART_CATEGORIES, useStore } from "../../data/store.jsx";

const PAGE_SIZE = 4;
const sorters = {
  relevance: { label: "Relevancia", fn: () => 0 },
  stockAsc: { label: "Stock: menor a mayor", fn: (a, b) => a.stock - b.stock },
  stockDesc: { label: "Stock: mayor a menor", fn: (a, b) => b.stock - a.stock },
  priceAsc: { label: "Precio: menor a mayor", fn: (a, b) => a.price - b.price },
  priceDesc: { label: "Precio: mayor a menor", fn: (a, b) => b.price - a.price },
};

export default function Inventory() {
  const { parts } = useStore();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [onlyCritical, setOnlyCritical] = useState(false);
  const [sort, setSort] = useState("relevance");
  const [page, setPage] = useState(1);

  const totalUnits = parts.reduce((s, p) => s + p.stock, 0);
  const critical = parts.filter((p) => p.stock <= p.min);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return parts
      .filter((p) =>
        (!category || p.category === category) &&
        (!onlyCritical || p.stock <= p.min) &&
        (!q || `${p.sku} ${p.name} ${p.compat}`.toLowerCase().includes(q))
      )
      .sort(sorters[sort].fn);
  }, [parts, query, category, onlyCritical, sort]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const rows = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const reset = (fn) => (v) => { fn(v); setPage(1); };

  return (
    <div className="staff-page">
      <div className="page-head">
        <h1 className="page-title">Inventario de Repuestos</h1>
        <Link to="/taller/inventario/nuevo" className="btn btn--primary">
          <PlusCircle size={17} aria-hidden="true" /> Nuevo Repuesto (SKU)
        </Link>
      </div>

      <div className="kpis kpis--2">
        <div className="kpi kpi--bubble">
          <div>
            <p className="mono-label">Stock total de repuestos</p>
            <p className="kpi__value">{totalUnits.toLocaleString("en-US")} <span className="kpi__delta kpi__delta--teal">{parts.length} SKU activos</span></p>
          </div>
          <span className="kpi__bubble"><ClipboardCheck size={22} aria-hidden="true" /></span>
        </div>
        <button type="button" className={`kpi kpi--bubble kpi--danger${onlyCritical ? " is-on" : ""}`} onClick={() => reset(setOnlyCritical)(!onlyCritical)} aria-pressed={onlyCritical}>
          <div>
            <p className="mono-label">Alertas de stock crítico</p>
            <p className="kpi__value">{critical.length} <span className="badge-danger">{onlyCritical ? "Mostrando críticos" : "Reponer urgente"}</span></p>
          </div>
          <span className="kpi__bubble"><TriangleAlert size={22} aria-hidden="true" /></span>
        </button>
      </div>

      <div className="panel panel--tight">
        <div className="toolbar toolbar--plain">
          <label className="search search--grow">
            <Search size={18} aria-hidden="true" />
            <input type="search" placeholder="Buscar por SKU (ej. SSD-NVME-2TB), descripción o marca..." value={query} onChange={(e) => reset(setQuery)(e.target.value)} aria-label="Buscar repuestos" />
          </label>
          <label className="select-chip">
            <SlidersHorizontal size={16} aria-hidden="true" />
            <select value={onlyCritical ? "critical" : "all"} onChange={(e) => reset(setOnlyCritical)(e.target.value === "critical")} aria-label="Filtros">
              <option value="all">Todos los estados</option>
              <option value="critical">Solo stock crítico</option>
            </select>
          </label>
          <label className="select-chip">
            <ArrowUpDown size={16} aria-hidden="true" />
            <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Ordenar">
              {Object.entries(sorters).map(([k, s]) => <option key={k} value={k}>{s.label}</option>)}
            </select>
          </label>
        </div>
        <div className="chips chips--scroll" role="tablist" aria-label="Categoría">
          <button type="button" role="tab" aria-selected={!category} className={`chip chip--mono${!category ? " is-active" : ""}`} onClick={() => reset(setCategory)("")}>
            Todos ({parts.length})
          </button>
          {PART_CATEGORIES.map((c) => (
            <button key={c} type="button" role="tab" aria-selected={category === c} className={`chip chip--mono${category === c ? " is-active" : ""}`} onClick={() => reset(setCategory)(c)}>
              {c} ({parts.filter((p) => p.category === c).length})
            </button>
          ))}
        </div>
      </div>

      <div className="table-card">
        <div className="list-head">
          <span className="mono-label">Listado de componentes</span>
          <span className="mono-label">Mostrando {rows.length} de {filtered.length} ítems</span>
        </div>
        {rows.length === 0 && <p className="empty">No hay repuestos con estos filtros.</p>}
        <ul className="parts">
          {rows.map((p) => {
            const low = p.stock <= p.min;
            return (
              <li key={p.sku} className={`part${low ? " part--low" : ""}`}>
                <span className="part__icon"><ItemIcon name={p.icon} size={22} /></span>
                <div className="part__main">
                  <p className="part__name">
                    {p.name}
                    <span className={`stock-badge${low ? " stock-badge--low" : ""}`}>{low ? "Stock crítico" : "En stock"}</span>
                  </p>
                  <p className="part__meta">
                    <span className="sku">SKU: {p.sku}</span>
                    <span className="part__compat"><Laptop size={14} aria-hidden="true" /> {p.compat}</span>
                  </p>
                </div>
                <p className={`part__stock${low ? " is-low" : ""}`}><strong>{p.stock} u.</strong> libres</p>
                <p className={`part__price${low ? " is-low" : ""}`}>{formatPEN(p.price)}</p>
                <Link to={`/taller/inventario/${encodeURIComponent(p.sku)}/editar`} className="icon-btn icon-btn--soft" aria-label={`Editar ${p.sku}`}>
                  <Pencil size={17} />
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="table-card__foot">
          <Pagination page={current} pages={pages} onChange={setPage} label={`Página ${current} de ${pages}`} />
        </div>
      </div>
    </div>
  );
}
