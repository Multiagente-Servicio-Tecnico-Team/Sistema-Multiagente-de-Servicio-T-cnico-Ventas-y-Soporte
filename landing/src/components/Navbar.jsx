import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Menu, X } from "lucide-react";
import Logo from "./Logo.jsx";
import { useStore } from "../data/store.jsx";

const links = [
  { href: "#plataforma", label: "Plataforma" },
  { href: "#agentes", label: "Agentes" },
  { href: "#flujo", label: "Flujo" },
  { href: "#seguridad", label: "Seguridad" },
];

export default function Navbar() {
  const { session } = useStore();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const close = () => setOpen(false);

  // Con sesión abierta se ofrece volver al área correspondiente en lugar de "Iniciar sesión".
  const account = session
    ? { to: session.role === "staff" ? "/taller" : "/portal/tickets", label: session.role === "staff" ? "Ir al panel" : "Ir a mi portal" }
    : { to: "/portal/acceso", label: "Iniciar sesión" };

  return (
    <header className={`nav${scrolled ? " nav--scrolled" : ""}`}>
      <div className="container nav__inner">
        <Logo />
        <nav className="nav__links" aria-label="Principal">
          {links.map((l) => (
            <a key={l.href} href={l.href}>{l.label}</a>
          ))}
        </nav>
        <div className="nav__actions">
          <Link to={account.to} className="nav__login">{account.label}</Link>
          <a href="#demo" className="btn btn--primary">
            <ArrowRight size={18} aria-hidden="true" /> Solicitar demo
          </a>
        </div>
        <button
          type="button"
          className="nav__toggle"
          aria-label={open ? "Cerrar menú" : "Abrir menú"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
      {open && (
        <div className="nav__mobile">
          {links.map((l) => (
            <a key={l.href} href={l.href} onClick={close}>{l.label}</a>
          ))}
          <Link to={account.to} onClick={close}>{account.label}</Link>
          {!session && <Link to="/taller/acceso" onClick={close}>Acceso para el taller</Link>}
          <a href="#demo" className="btn btn--primary" onClick={close}>
            <ArrowRight size={18} aria-hidden="true" /> Solicitar demo
          </a>
        </div>
      )}
    </header>
  );
}
