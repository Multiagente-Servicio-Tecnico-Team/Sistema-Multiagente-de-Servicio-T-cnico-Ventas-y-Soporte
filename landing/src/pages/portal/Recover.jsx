import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, AtSign, Info, LoaderCircle, MailCheck, ShieldCheck } from "lucide-react";
import { BackLink, Field, InputIcon } from "../../components/ui.jsx";
import { EMAIL_RE } from "../../data/store.jsx";
import { authApi as defaultApi, MESSAGES } from "../../api/auth.js";
import { FormAlert } from "./Login.jsx";

export default function Recover({ api = defaultApi }) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setFormError("");
    if (!EMAIL_RE.test(email.trim())) {
      setError("Ingresa un correo electrónico válido.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await api.requestPasswordReset({ email });
      setSent(true);
    } catch (err) {
      setFormError(err?.message || MESSAGES.unexpected);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-stack">
      <BackLink to="/portal/acceso" mono>Volver a iniciar sesión</BackLink>
      <div className="auth-card auth-card--accent auth-card--left">
        <div className="auth-card__body">
          <span className="badge"><ShieldCheck size={14} aria-hidden="true" />Seguridad de cuenta · Soporte técnico</span>
          {sent ? (
            <div className="success-state">
              <span className="success-state__icon"><MailCheck size={26} aria-hidden="true" /></span>
              <h1 className="auth-title">Revisa tu correo</h1>
              <p className="auth-sub">
                Si <strong>{email.trim()}</strong> está registrado, recibirás un enlace de restablecimiento válido durante 15 minutos.
                Revisa también tu carpeta de spam.
              </p>
              <div className="btn-row btn-row--start">
                <button type="button" className="btn btn--ghost" onClick={() => setSent(false)}>Usar otro correo</button>
                {api.mode === "mock" && (
                  <Link to="/portal/restablecer?token=demo" className="btn btn--soft">Abrir enlace de prueba</Link>
                )}
              </div>
              {api.mode === "mock" && (
                <p className="demo-note"><Info size={14} aria-hidden="true" /> Modo demostración: no se envían correos; usa el enlace de prueba.</p>
              )}
            </div>
          ) : (
            <>
              <h1 className="auth-title">¿Olvidaste tu contraseña?</h1>
              <p className="auth-sub">
                Introduce el correo electrónico asociado a tu cuenta de TechFix.AI para recibir un enlace seguro de
                restablecimiento de contraseña temporal (válido durante 15 minutos).
              </p>
              <form className="form" onSubmit={submit} noValidate aria-busy={loading}>
                <FormAlert>{formError}</FormAlert>
                <Field
                  label="Correo Electrónico Registrado"
                  htmlFor="recover-email"
                  error={error}
                  hint={<><Info size={13} aria-hidden="true" /> Enviaremos una llave criptográfica temporal a esta dirección.</>}
                >
                  <InputIcon icon={AtSign}>
                    <input
                      id="recover-email"
                      type="email"
                      className="input input--icon"
                      placeholder="ejemplo@tudominio.com"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      aria-invalid={!!error || undefined}
                    />
                  </InputIcon>
                </Field>
                <button type="submit" className="btn btn--primary btn--block btn--lg" disabled={loading}>
                  {loading ? (
                    <><LoaderCircle size={18} className="spin" aria-hidden="true" /> Enviando…</>
                  ) : (
                    <>Enviar Enlace de Restablecimiento <ArrowRight size={18} aria-hidden="true" /></>
                  )}
                </button>
              </form>
            </>
          )}
          <Link to="/portal/acceso" className="link link--strong">← Volver a Iniciar Sesión</Link>
        </div>
      </div>
    </div>
  );
}
