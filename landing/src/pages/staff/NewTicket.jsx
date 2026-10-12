import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Banknote, CircleCheck, Laptop, ReceiptText, UserRound } from "lucide-react";
import { BackLink, Field } from "../../components/ui.jsx";
import { EMAIL_RE, formatPEN, parseMoney, TICKET_CATEGORIES, useStore } from "../../data/store.jsx";

const methods = ["Yape/Plin", "Efectivo", "Tarjeta"];

export default function NewTicket() {
  const { staffTickets, dispatch } = useStore();
  const navigate = useNavigate();
  const [form, setForm] = useState({ client: "", phone: "", email: "", device: "", issue: "", category: "Reparación", advance: "", method: "Yape/Plin" });
  const [errors, setErrors] = useState({});
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const nextId = `TCK-${Math.max(...staffTickets.map((t) => Number(t.id.split("-")[1]))) + 1}`;

  const submit = (e) => {
    e.preventDefault();
    const next = {};
    if (form.client.trim().length < 3) next.client = "Ingresa el nombre o razón social.";
    if (form.phone.replace(/\D/g, "").length < 9) next.phone = "Ingresa un número de 9 dígitos.";
    if (form.email.trim() && !EMAIL_RE.test(form.email.trim())) next.email = "Correo no válido.";
    if (form.device.trim().length < 2) next.device = "Indica el equipo, marca y modelo.";
    if (form.issue.trim().length < 5) next.issue = "Describe la falla o solicitud.";
    const advance = form.advance.trim() ? parseMoney(form.advance) : null;
    if (form.advance.trim() && advance === null) next.advance = "Usa un importe como 30 o 30.00.";
    setErrors(next);
    if (Object.keys(next).length) return;

    dispatch({
      type: "createTicket",
      ticket: {
        client: form.client.trim(),
        phone: `+51 ${form.phone.replace(/\D/g, "").replace(/(\d{3})(\d{3})(\d{3}).*/, "$1 $2 $3")}`,
        email: form.email.trim(),
        device: form.device.trim(),
        issue: form.issue.trim(),
        category: form.category,
        advance,
        method: advance !== null ? form.method : null,
        payment: advance !== null ? `Adelanto ${formatPEN(advance)} · ${form.method}` : "Pendiente",
      },
    });
    navigate(`/taller/tickets/${nextId}`);
  };

  return (
    <div className="staff-page">
      <BackLink to="/taller">Volver a Gestión de Tickets</BackLink>
      <h1 className="page-title page-title--sm">Crear Nuevo Ticket</h1>

      <form className="new-ticket" onSubmit={submit} noValidate>
        <section className="panel">
          <div className="panel__head">
            <span className="icon-tile icon-tile--sm"><UserRound size={18} aria-hidden="true" /></span>
            <div><h2>1. Datos del Cliente</h2><p>Recepción rápida en mostrador</p></div>
          </div>
          <Field label="Nombre Completo / Razón Social" htmlFor="nt-client" required error={errors.client}>
            <input id="nt-client" className="input" placeholder="Valeria Marcela Gómez Rivas" value={form.client} onChange={set("client")} autoComplete="off" />
          </Field>
          <div className="grid-2">
            <Field label="WhatsApp / Celular" htmlFor="nt-phone" required error={errors.phone}>
              <div className="input-prefix">
                <span>+51</span>
                <input id="nt-phone" type="tel" inputMode="tel" className="input" placeholder="987 654 321" value={form.phone} onChange={set("phone")} autoComplete="off" />
              </div>
            </Field>
            <Field label={<>Correo Electrónico <span className="muted">(Opcional)</span></>} htmlFor="nt-email" error={errors.email}>
              <input id="nt-email" type="email" className="input" placeholder="cliente@empresa.pe" value={form.email} onChange={set("email")} autoComplete="off" />
            </Field>
          </div>
        </section>

        <div className="new-ticket__col">
          <section className="panel">
            <div className="panel__head">
              <span className="icon-tile icon-tile--sm"><Laptop size={18} aria-hidden="true" /></span>
              <div><h2>2. Detalle del Equipo y Falla</h2><p>Identificación y motivo de ingreso</p></div>
            </div>
            <div className="grid-2">
              <Field label="Equipo / Marca y Modelo" htmlFor="nt-device" required error={errors.device}>
                <input id="nt-device" className="input" placeholder="Laptop Lenovo Legion 5 15ACH6" value={form.device} onChange={set("device")} />
              </Field>
              <Field label="Categoría" htmlFor="nt-cat">
                <select id="nt-cat" className="input select" value={form.category} onChange={set("category")}>
                  {TICKET_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                </select>
              </Field>
            </div>
            <Field label="Detalle de la Falla o Solicitud" htmlFor="nt-issue" required error={errors.issue}>
              <textarea id="nt-issue" className="input textarea" rows={4} placeholder="Describe síntomas, accesorios recibidos y lo que solicita el cliente." value={form.issue} onChange={set("issue")} />
            </Field>
          </section>

          <section className="panel">
            <div className="panel__head">
              <span className="icon-tile icon-tile--sm"><Banknote size={18} aria-hidden="true" /></span>
              <div><h2>3. Costo y Adelanto</h2><p>Adelanto cobrado en ventanilla (el presupuesto lo emite el diagnóstico)</p></div>
            </div>
            <div className="grid-2 grid-2--end">
              <Field label="Monto Cobrado / Adelanto" htmlFor="nt-adv" error={errors.advance}>
                <div className="input-prefix input-prefix--money">
                  <span>S/.</span>
                  <input id="nt-adv" inputMode="decimal" className="input" placeholder="0.00" value={form.advance} onChange={set("advance")} />
                </div>
              </Field>
              <fieldset className="field">
                <legend className="field__label">Método de Pago</legend>
                <div className="radio-pills">
                  {methods.map((m) => (
                    <label key={m} className={`radio-pill${form.method === m ? " is-active" : ""}`}>
                      <input type="radio" name="method" value={m} checked={form.method === m} onChange={set("method")} />
                      {m}
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>
          </section>
        </div>

        <div className="panel submit-bar">
          <div className="submit-bar__info">
            <span className="icon-tile icon-tile--sm"><ReceiptText size={18} aria-hidden="true" /></span>
            <div><strong>Listo para Emisión Rápida</strong><p className="mono-small">Ticket #{nextId}</p></div>
          </div>
          <button type="submit" className="btn btn--primary btn--lg">
            <CircleCheck size={19} aria-hidden="true" /> Generar Ticket
          </button>
        </div>
      </form>
    </div>
  );
}
