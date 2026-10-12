import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Archive, Banknote, Barcode, Laptop, Lock, Save, X } from "lucide-react";
import { BackLink, Field, InputIcon } from "../../components/ui.jsx";
import { centsToInput, parseMoney, PART_CATEGORIES, useStore } from "../../data/store.jsx";

const SKU_RE = /^[A-Z0-9]+(?:-[A-Z0-9]+)*$/;

/** Alta de un SKU nuevo (sin parámetro) o edición y ajuste de stock (con :sku). */
export default function PartForm() {
  const { sku } = useParams();
  const { parts, dispatch } = useStore();
  const navigate = useNavigate();
  const existing = sku ? parts.find((p) => p.sku === sku) : null;
  const editing = Boolean(sku);

  const [form, setForm] = useState(() => ({
    sku: existing?.sku ?? "",
    name: existing?.name ?? "",
    category: existing?.category ?? PART_CATEGORIES[1],
    compat: existing?.compat ?? "",
    stock: existing ? String(existing.stock) : "",
    min: existing ? String(existing.min) : "",
    price: existing ? centsToInput(existing.price) : "",
  }));
  const [errors, setErrors] = useState({});
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: key === "sku" ? e.target.value.toUpperCase() : e.target.value }));

  if (editing && !existing) {
    return (
      <div className="staff-page">
        <BackLink to="/taller/inventario">Volver a Inventario de Repuestos</BackLink>
        <div className="panel empty-panel">
          <h1 className="page-title">Repuesto no encontrado</h1>
          <p>No existe el SKU <strong>{sku}</strong>.</p>
          <Link to="/taller/inventario" className="btn btn--primary">Volver al inventario</Link>
        </div>
      </div>
    );
  }

  const submit = (e) => {
    e.preventDefault();
    const next = {};
    const code = form.sku.trim();
    if (!editing) {
      if (!SKU_RE.test(code)) next.sku = "Usa mayúsculas, números y guiones (ej. SSD-NVME-2TB-KC).";
      else if (parts.some((p) => p.sku === code)) next.sku = "Este SKU ya existe en el inventario.";
    }
    if (form.name.trim().length < 3) next.name = "Ingresa el nombre del componente.";
    const stock = /^\d+$/.test(form.stock.trim()) ? Number(form.stock) : null;
    const min = /^\d+$/.test(form.min.trim()) ? Number(form.min) : null;
    const price = parseMoney(form.price);
    if (stock === null) next.stock = "Cantidad entera mayor o igual a 0.";
    if (min === null) next.min = "Cantidad entera mayor o igual a 0.";
    if (price === null || price === 0) next.price = "Importe válido, ej. 114.75.";
    setErrors(next);
    if (Object.keys(next).length) return;

    dispatch({
      type: "savePart",
      part: { sku: editing ? existing.sku : code, name: form.name.trim(), category: form.category, compat: form.compat.trim(), stock, min, price },
    });
    navigate("/taller/inventario");
  };

  return (
    <div className="staff-page staff-page--form">
      <BackLink to="/taller/inventario">Volver a Inventario de Repuestos</BackLink>
      <h1 className="page-title">{editing ? "Editar Repuesto y Ajustar Stock" : "Registrar Nuevo Repuesto (SKU)"}</h1>

      <form onSubmit={submit} noValidate className="stack">
        <section className="panel">
          <div className="panel__head">
            {editing ? <span className="icon-tile icon-tile--sm"><Archive size={18} aria-hidden="true" /></span> : <span className="step-num">01</span>}
            <div>
              <h2>{editing ? "Datos del Repuesto" : "Identificación y Categoría"}</h2>
              <p>Especificaciones técnicas, catalogación y compatibilidad del componente</p>
            </div>
          </div>
          <div className="grid-2">
            <Field
              label="Código SKU"
              htmlFor="pf-sku"
              required={!editing}
              error={errors.sku}
              aside={editing && <span className="muted small">Identificador único</span>}
            >
              <InputIcon icon={editing ? null : Barcode} suffix={editing ? <Lock size={16} aria-label="No editable" /> : null}>
                <input id="pf-sku" className={`input mono${editing ? " input--locked" : " input--icon"}`} placeholder="SSD-NVME-2TB-KC" value={form.sku} onChange={set("sku")} readOnly={editing} />
              </InputIcon>
            </Field>
            <Field label="Categoría de Componente" htmlFor="pf-cat" required>
              <select id="pf-cat" className="input select" value={form.category} onChange={set("category")}>
                {PART_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Nombre y Descripción del Componente" htmlFor="pf-name" required error={errors.name}>
            <input id="pf-name" className="input" placeholder="SSD NVMe M.2 2TB Kingston KC3000 PCIe 4.0" value={form.name} onChange={set("name")} />
          </Field>
          <Field label="Equipos y Modelos Compatibles" htmlFor="pf-compat">
            <InputIcon icon={Laptop}>
              <input id="pf-compat" className="input input--icon" placeholder="Dell XPS 13/15, ThinkPad X1 Carbon, Universales NVMe M.2 2280" value={form.compat} onChange={set("compat")} />
            </InputIcon>
          </Field>
        </section>

        <section className="panel">
          <div className="panel__head">
            {editing ? <span className="icon-tile icon-tile--sm"><Banknote size={18} aria-hidden="true" /></span> : <span className="step-num">02</span>}
            <div>
              <h2>Stock Operativo y Precios</h2>
              <p>Cantidades disponibles para órdenes de trabajo, alertas de reposición y tarifa de cotización</p>
            </div>
          </div>
          <div className="grid-3">
            <Field label={editing ? "Stock Actual Disponible" : "Cantidad Inicial"} htmlFor="pf-stock" required error={errors.stock}>
              <InputIcon suffix="Unid.">
                <input id="pf-stock" inputMode="numeric" className="input" placeholder="0" value={form.stock} onChange={set("stock")} />
              </InputIcon>
            </Field>
            <Field label="Stock Mínimo de Alerta" htmlFor="pf-min" required error={errors.min}>
              <InputIcon suffix="Unid.">
                <input id="pf-min" inputMode="numeric" className="input" placeholder="0" value={form.min} onChange={set("min")} />
              </InputIcon>
            </Field>
            <Field label="Precio de Venta / Cotización (PEN)" htmlFor="pf-price" required error={errors.price}>
              <div className="input-prefix input-prefix--money">
                <span>S/.</span>
                <input id="pf-price" inputMode="decimal" className="input mono" placeholder="0.00" value={form.price} onChange={set("price")} />
              </div>
            </Field>
          </div>
        </section>

        <div className="form-actions">
          <Link to="/taller/inventario" className="btn btn--ghost"><X size={17} aria-hidden="true" /> Cancelar</Link>
          <button type="submit" className="btn btn--primary btn--lg">
            <Save size={18} aria-hidden="true" /> {editing ? "Guardar Cambios" : "Guardar Repuesto"}
          </button>
        </div>
      </form>
    </div>
  );
}
