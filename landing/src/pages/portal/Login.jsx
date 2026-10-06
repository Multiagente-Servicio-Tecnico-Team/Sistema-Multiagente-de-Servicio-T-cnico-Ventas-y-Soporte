import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, AtSign, Info, Lock, LoaderCircle, TriangleAlert } from "lucide-react";
import { Field, InputIcon, PasswordInput } from "../../components/ui.jsx";
import { EMAIL_RE, useStore } from "../../data/store.jsx";
import { areaForRole, authApi as defaultApi, fullName, MESSAGES } from "../../api/auth.js";

export function FormAlert({ children }) {
  if (!children) return null;
  return (
    <div className="form-alert" role="alert">
      <TriangleAlert size={16} aria-hidden="true" /> <span>{children}</span>
    </div>
  );
}

/**
 * Formulario de acceso reutilizado por el portal del cliente y por el personal del taller.
 * Llama a POST /login mediante el cliente de autenticación (o al simulador si no hay backend).
 */
export function LoginForm({ role, badge, title, subtitle, defaultTo, footer, api = defaultApi }) {
  const { session, login, logout } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);

  // Si ya hay sesión con este rol, el formulario no tiene sentido: ir directo al área.
  if (session?.role === role && !loading) return <Navigate to={location.state?.from || defaultTo} replace />;

  const submit = async (e) => {
    e.preventDefault();
    if (loading) return;
    const next = {};
    if (!EMAIL_RE.test(email.trim())) next.email = "Ingresa un correo electrónico válido.";
    if (!password) next.password = "Ingresa tu contraseña.";
    setErrors(next);
    setFormError("");
    if (Object.keys(next).length) return;

    setLoading(true);
    try {
      const usuario = await api.login({ email, password });
      setPassword("");
      // El rol lo decide el servidor (tabla users); la pantalla solo indica el área esperada.
      const area = areaForRole(usuario.rol, role);
      if (role === "staff" && area === "client") {
        // El servidor ya abrió sesión: se cierra en ambos lados para no dejar estados distintos.
        await api.logout?.();
        logout();
        setFormError(MESSAGES.notStaff);
        setLoading(false);
        return;
      }
      login({ role: area, email: usuario.email, name: fullName(usuario) || usuario.email });
      const target = area === role ? location.state?.from || defaultTo : "/taller";
      navigate(target, { replace: true });
    } catch (err) {
      setFormError(err?.message || MESSAGES.unexpected);
      setLoading(false);
    }
  };

  return (
    <div className="auth-card">
      <div className="auth-card__body">
        <span className="badge"><span className="pill__dot" />{badge}</span>
        <h1 className="auth-title">{title}</h1>
        <p className="auth-sub">{subtitle}</p>

        <form className="form" onSubmit={submit} noValidate aria-busy={loading}>
          <FormAlert>{formError}</FormAlert>
          <Field label="Correo electrónico" htmlFor="email" error={errors.email} className="field--mono-label">
            <InputIcon icon={AtSign}>
              <input
                id="email"
                type="email"
                className="input input--icon"
                placeholder="tu.correo@ejemplo.com"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-invalid={!!errors.email || undefined}
              />
            </InputIcon>
          </Field>
          <Field label="Contraseña" htmlFor="password" error={errors.password} className="field--mono-label">
            <PasswordInput
              id="password"
              icon={Lock}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              invalid={!!errors.password}
            />
          </Field>
          <Link to="/portal/recuperar" className="link link--sm form__right">¿Olvidaste tu contraseña?</Link>
          <button type="submit" className="btn btn--primary btn--block btn--lg" disabled={loading}>
            {loading ? (
              <><LoaderCircle size={18} className="spin" aria-hidden="true" /> Ingresando…</>
            ) : (
              <>Iniciar Sesión <ArrowRight size={18} aria-hidden="true" /></>
            )}
          </button>
          {api.mode === "mock" && (
            <p className="demo-note"><Info size={14} aria-hidden="true" /> Modo demostración sin backend: cualquier correo válido y contraseña permiten ingresar.</p>
          )}
        </form>
      </div>
      <div className="auth-card__foot">{footer}</div>
    </div>
  );
}

export default function Login() {
  return (
    <LoginForm
      role="client"
      badge="Portal de clientes"
      title="Acceder a mi Portal de Servicio"
      subtitle="Gestiona tus tickets de reparación, aprueba presupuestos y chatea con nuestro agente IA en tiempo real."
      defaultTo="/portal/tickets"
      footer={
        <>
          <p>¿Aún no tienes cuenta? <Link to="/portal/registro" className="link">Regístrate gratis aquí</Link></p>
          <p>¿Eres parte del taller? <Link to="/taller/acceso" className="link">Acceso para personal</Link></p>
        </>
      }
    />
  );
}
