import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Archive, Menu, PlusCircle, Wrench, X, ExternalLink } from "lucide-react";
import Logo from "../components/Logo.jsx";
import { UserMenu } from "./PortalLayout.jsx";

const links = [
  { to: "/taller", label: "Taller & Cola Triage", icon: Wrench, end: true },
  { to: "/taller/inventario", label: "Stock y Repuestos", icon: Archive },
];

export default function StaffLayout() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => setOpen(false), [pathname]);

  // Mantiene resaltado "Taller" también en el detalle y alta de tickets.
  const isActive = (link) => (link.end ? pathname === "/taller" || pathname.startsWith("/taller/tickets") : pathname.startsWith(link.to));

  return (
    <div className="staff">
      <aside className={`staff-side${open ? " is-open" : ""}`} aria-label="Navegación del taller">
        <div className="staff-side__head">
          <Logo />
          <button type="button" className="icon-btn staff-side__close" onClick={() => setOpen(false)} aria-label="Cerrar menú">
            <X size={20} />
          </button>
        </div>
        <nav className="staff-side__nav">
          {links.map((l) => {
            const Icon = l.icon;
            return (
              <NavLink key={l.to} to={l.to} className={() => `side-link${isActive(l) ? " is-active" : ""}`}>
                <Icon size={18} aria-hidden="true" /> {l.label}
              </NavLink>
            );
          })}
        </nav>
        <p className="staff-side__note">
          <span className="pill pill--green"><span className="pill__dot" />4 agentes activos</span>
        </p>
      </aside>
      {open && <div className="staff-scrim" onClick={() => setOpen(false)} aria-hidden="true" />}

      <div className="staff-body">
        <header className="staff-top">
          <button type="button" className="icon-btn staff-top__menu" onClick={() => setOpen(true)} aria-label="Abrir menú" aria-expanded={open}>
            <Menu size={22} />
          </button>
          <div className="staff-top__actions">
            <Link to="/taller/tickets/nuevo" className="top-link">
              <PlusCircle size={16} aria-hidden="true" /> <span className="hide-xs">Nuevo Ticket Manual</span>
            </Link>
            <Link to="/" className="top-link hide-sm">
              <ExternalLink size={16} aria-hidden="true" /> Sitio web
            </Link>
            <UserMenu />
          </div>
        </header>
        <main className="staff-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
