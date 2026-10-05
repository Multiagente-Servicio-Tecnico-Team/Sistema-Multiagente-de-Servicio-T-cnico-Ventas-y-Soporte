import { Link, Outlet } from "react-router-dom";
import { UserRound } from "lucide-react";
import Logo from "../components/Logo.jsx";

export function AppFooterLegal() {
  return (
    <footer className="auth-footer">
      <span className="auth-footer__dot" aria-hidden="true" />
      <nav aria-label="Legal">
        <Link to="/ayuda#legal">Términos de Servicio</Link>
        <Link to="/ayuda#legal">Política de Privacidad</Link>
        <Link to="/ayuda#legal">Certificaciones de Seguridad</Link>
      </nav>
      <p>© 2026 TechFix.AI Inc. Todos los derechos reservados.</p>
    </footer>
  );
}

export default function AuthLayout() {
  return (
    <div className="auth">
      <header className="auth-header">
        <Logo />
        <nav className="auth-header__nav" aria-label="Ayuda">
          <Link to="/ayuda" className="hide-xs">Soporte Técnico</Link>
          <Link to="/ayuda#faq">Preguntas Frecuentes</Link>
          <span className="lang-badge" aria-label="Idioma: español">ES</span>
          <Link to="/portal/acceso" className="avatar" aria-label="Acceder a mi cuenta">
            <UserRound size={18} />
          </Link>
        </nav>
      </header>
      <main className="auth-main">
        <Outlet />
      </main>
      <AppFooterLegal />
    </div>
  );
}
