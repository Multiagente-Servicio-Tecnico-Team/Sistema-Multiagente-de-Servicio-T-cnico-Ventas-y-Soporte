import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LogOut, UserRound } from "lucide-react";
import Logo from "../components/Logo.jsx";
import { useStore } from "../data/store.jsx";

export function UserMenu({ extra }) {
  const { session, logout } = useStore();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const signOut = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="user-menu" ref={ref}>
      <button
        type="button"
        className="avatar avatar--online"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Menú de usuario"
        onClick={() => setOpen((v) => !v)}
      >
        <UserRound size={18} />
      </button>
      {open && (
        <div className="user-menu__panel" role="menu">
          <p className="user-menu__name">{session?.name}</p>
          <p className="user-menu__mail">{session?.email}</p>
          {extra}
          <button type="button" role="menuitem" className="user-menu__item" onClick={signOut}>
            <LogOut size={16} aria-hidden="true" /> Cerrar sesión
          </button>
        </div>
      )}
    </div>
  );
}

export default function PortalLayout() {
  return (
    <div className="portal">
      <header className="portal-header">
        <Logo />
        <nav className="portal-header__nav" aria-label="Portal del cliente">
          <NavLink to="/portal/asistente" className="tab-link">
            <span className="hide-xs">Nuevo Ticket / </span>Chat IA
          </NavLink>
          <NavLink to="/portal/tickets" className="tab-link">Mis Tickets</NavLink>
        </nav>
        <UserMenu />
      </header>
      <main className="portal-main">
        <Outlet />
      </main>
      <footer className="portal-footer">
        <p>
          <strong>TechFix<span className="logo__ai">.AI</span></strong>
          <span className="mono-small">Plataforma Inteligente de Servicio Técnico</span>
        </p>
        <p>© 2026 TechFix.AI. Diagnóstico autónomo y gestión de triage de hardware.</p>
      </footer>
    </div>
  );
}
