import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, CircleCheck, LinkIcon, LoaderCircle, ShieldCheck } from "lucide-react";
import { BackLink } from "../../components/ui.jsx";
import PasswordFields, { isStrongPassword } from "../../components/PasswordFields.jsx";
import { authApi as defaultApi, MESSAGES } from "../../api/auth.js";
import { FormAlert } from "./Login.jsx";

/**
 * Pantalla creada: destino del enlace que envía /recuperar.
 * Lee ?token= de la URL y envía POST /restablecer { token, password }.
 */
export default function Reset({ api = defaultApi }) {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  // Un enlace distinto reinicia el formulario y sus estados.
  return <ResetForm key={token} token={token} api={api} />;
}

function ResetForm({ token, api }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [tokenError, setTokenError] = useState(token ? "" : MESSAGES.invalidToken);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (loading) return;
    const next = {};
    if (!isStrongPassword(password)) next.password = "La contraseña no cumple todos los requisitos.";
    if (!confirm || confirm !== password) next.confirm = "Las contraseñas no coinciden.";
    setErrors(next);
    setFormError("");
    if (Object.keys(next).length) return;

    setLoading(true);
    try {
      await api.resetPassword({ token, password });
      setPassword("");
      setConfirm("");
      setDone(true);
    } catch (err) {
      if (err?.code === "invalid_token") setTokenError(err.message);
      else setFormError(err?.message || MESSAGES.unexpected);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-stack">
      <BackLink to="/portal/acceso" mono>Volver a iniciar sesión</BackLink>
      <div className="auth-card auth-card--accent auth-card--left">
        <div className="auth-card__body">
          <span className="badge"><ShieldCheck size={14} aria-hidden="true" />Seguridad de cuenta · Nueva contraseña</span>

          {done ? (
            <div className="success-state">
              <span className="success-state__icon"><CircleCheck size={26} aria-hidden="true" /></span>
              <h1 className="auth-title">Contraseña actualizada</h1>
              <p className="auth-sub">Ya puedes ingresar a tu portal con la nueva contraseña. Por seguridad, el enlace dejó de ser válido.</p>
              <Link to="/portal/acceso" className="btn btn--primary">Iniciar sesión <ArrowRight size={18} aria-hidden="true" /></Link>
            </div>
          ) : tokenError ? (
            <div className="success-state">
              <span className="success-state__icon success-state__icon--warn"><LinkIcon size={24} aria-hidden="true" /></span>
              <h1 className="auth-title">Enlace no válido</h1>
              <p className="auth-sub">{tokenError} Los enlaces de restablecimiento duran 15 minutos y solo pueden usarse una vez.</p>
              <Link to="/portal/recuperar" className="btn btn--primary">Solicitar un nuevo enlace <ArrowRight size={18} aria-hidden="true" /></Link>
            </div>
          ) : (
            <>
              <h1 className="auth-title">Crea una nueva contraseña</h1>
              <p className="auth-sub">Elige una contraseña segura que no hayas usado antes en TechFix.AI.</p>
              <form className="form" onSubmit={submit} noValidate aria-busy={loading}>
                <FormAlert>{formError}</FormAlert>
                <PasswordFields
                  idPrefix="reset"
                  label="Nueva Contraseña"
                  password={password}
                  confirm={confirm}
                  onPassword={(e) => setPassword(e.target.value)}
                  onConfirm={(e) => setConfirm(e.target.value)}
                  errors={errors}
                />
                <button type="submit" className="btn btn--primary btn--block btn--lg" disabled={loading}>
                  {loading ? (
                    <><LoaderCircle size={18} className="spin" aria-hidden="true" /> Guardando…</>
                  ) : (
                    <>Guardar Nueva Contraseña <ArrowRight size={18} aria-hidden="true" /></>
                  )}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
