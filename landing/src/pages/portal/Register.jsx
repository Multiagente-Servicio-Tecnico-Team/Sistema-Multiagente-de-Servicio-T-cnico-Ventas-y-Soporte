import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, BellRing, CircleCheck, Contact, LoaderCircle, Mail, Smartphone } from "lucide-react";
import { Field, InputIcon } from "../../components/ui.jsx";
import PasswordFields, { isStrongPassword } from "../../components/PasswordFields.jsx";
import { EMAIL_RE, useStore } from "../../data/store.jsx";
import { authApi as defaultApi, MESSAGES, toE164 } from "../../api/auth.js";
import { FormAlert } from "./Login.jsx";

export { PASSWORD_RULES } from "../../components/PasswordFields.jsx";

// Campos del contrato POST /registro -> campos del formulario.
const API_FIELDS = { nombre: "name", email: "email", telefono: "phone", password: "password" };

/** Valida el formulario de registro; devuelve un objeto { campo: mensaje }. */
export function validateRegister(form) {
  const errors = {};
  if (form.name.trim().length < 3) errors.name = "Ingresa tu nombre y apellido.";
  if (!EMAIL_RE.test(form.email.trim())) errors.email = "Ingresa un correo electrónico válido.";
  if (!/^\d{9}$/.test(form.phone.replace(/\D/g, ""))) errors.phone = "Ingresa un número móvil de 9 dígitos.";
  if (!isStrongPassword(form.password)) errors.password = "La contraseña no cumple todos los requisitos.";
  if (!form.confirm || form.confirm !== form.password) errors.confirm = "Las contraseñas no coinciden.";
  if (!form.terms) errors.terms = "Debes aceptar los términos para continuar.";
  return errors;
}

export default function Register({ api = defaultApi }) {
  const { session, login } = useStore();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", prefix: "+51", phone: "", password: "", confirm: "", terms: false });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));
  const emailOk = EMAIL_RE.test(form.email.trim());

  // Un cliente con sesión abierta no necesita registrarse de nuevo.
  if (session?.role === "client" && !loading) return <Navigate to="/portal/tickets" replace />;

  const submit = async (e) => {
    e.preventDefault();
    if (loading) return;
    const next = validateRegister(form);
    setErrors(next);
    setFormError("");
    if (Object.keys(next).length) return;

    setLoading(true);
    try {
      const usuario = await api.register({
        nombre: form.name,
        email: form.email,
        telefono: toE164(form.prefix, form.phone),
        password: form.password,
      });
      login({ role: "client", email: usuario.email, name: usuario.nombre });
      navigate("/portal/tickets", { replace: true });
    } catch (err) {
      const field = API_FIELDS[err?.field];
      if (field) {
        setErrors({ [field]: err.message });
      } else {
        setFormError(err?.message || MESSAGES.unexpected);
      }
      setLoading(false);
    }
  };

  return (
    <div className="auth-card auth-card--wide">
      <div className="auth-card__body">
        <div className="auth-head-center">
          <h1 className="auth-title">Crear Cuenta de Cliente</h1>
          <p className="auth-sub">
            Únete a TechFix.AI para registrar tus dispositivos, solicitar triage inteligente y gestionar garantías en tiempo real.
          </p>
        </div>

        <form className="form" onSubmit={submit} noValidate aria-busy={loading}>
          <FormAlert>{formError}</FormAlert>
          <Field label="Nombre y Apellido" htmlFor="name" error={errors.name}>
            <InputIcon icon={Contact}>
              <input id="name" className="input input--icon" placeholder="Martín Gómez" autoComplete="name" value={form.name} onChange={set("name")} aria-invalid={!!errors.name || undefined} />
            </InputIcon>
          </Field>

          <Field label="Correo Electrónico" htmlFor="reg-email" error={errors.email}>
            <InputIcon icon={Mail} suffix={emailOk && !errors.email ? <CircleCheck size={18} className="ok" aria-label="Correo válido" /> : null}>
              <input id="reg-email" type="email" className="input input--icon" placeholder="tu.correo@ejemplo.com" autoComplete="email" value={form.email} onChange={set("email")} aria-invalid={!!errors.email || undefined} />
            </InputIcon>
          </Field>

          <Field
            label="Teléfono Móvil"
            htmlFor="phone"
            error={errors.phone}
            hint={<span className="hint-teal"><BellRing size={13} aria-hidden="true" /> Utilizado exclusivamente para avisos de retiro y actualizaciones de triage.</span>}
          >
            <div className="phone-row">
              <select className="input select phone-row__prefix" value={form.prefix} onChange={set("prefix")} aria-label="Código de país">
                <option value="+51">🇵🇪 +51</option>
                <option value="+56">🇨🇱 +56</option>
                <option value="+57">🇨🇴 +57</option>
                <option value="+52">🇲🇽 +52</option>
              </select>
              <InputIcon icon={Smartphone}>
                <input id="phone" type="tel" inputMode="tel" className="input input--icon" placeholder="987 654 321" autoComplete="tel-national" value={form.phone} onChange={set("phone")} aria-invalid={!!errors.phone || undefined} />
              </InputIcon>
            </div>
          </Field>

          <PasswordFields
            password={form.password}
            confirm={form.confirm}
            onPassword={set("password")}
            onConfirm={set("confirm")}
            errors={errors}
          />

          <div className="field">
            <label className="check">
              <input type="checkbox" checked={form.terms} onChange={set("terms")} />
              <span>
                Acepto los <Link to="/ayuda#legal" className="link">Términos de Servicio</Link> y la{" "}
                <Link to="/ayuda#legal" className="link">Política de Privacidad de Datos</Link> de TechFix.AI.
              </span>
            </label>
            {errors.terms && <p className="field__error" role="alert">{errors.terms}</p>}
          </div>

          <button type="submit" className="btn btn--primary btn--block btn--lg" disabled={loading}>
            {loading ? (
              <><LoaderCircle size={18} className="spin" aria-hidden="true" /> Creando cuenta…</>
            ) : (
              <>Crear Mi Cuenta <ArrowRight size={18} aria-hidden="true" /></>
            )}
          </button>
          <p className="auth-alt">¿Ya tienes una cuenta registrada? <Link to="/portal/acceso" className="link">Inicia sesión aquí</Link></p>
        </form>
      </div>
    </div>
  );
}
