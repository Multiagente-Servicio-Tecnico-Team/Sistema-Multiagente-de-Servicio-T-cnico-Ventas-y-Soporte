import { Link } from "react-router-dom";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="auth-card">
      <div className="auth-card__body auth-head-center">
        <span className="success-state__icon"><Compass size={26} aria-hidden="true" /></span>
        <p className="mono-label">Error 404</p>
        <h1 className="auth-title">Esta página no existe</h1>
        <p className="auth-sub">Puede que el enlace esté incompleto o que la página se haya movido.</p>
        <div className="btn-row">
          <Link to="/" className="btn btn--primary">Ir al inicio</Link>
          <Link to="/portal/acceso" className="btn btn--ghost">Portal de clientes</Link>
        </div>
      </div>
    </div>
  );
}
