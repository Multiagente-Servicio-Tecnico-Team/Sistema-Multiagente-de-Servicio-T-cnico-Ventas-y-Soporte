import { Link } from "react-router-dom";
import Logo from "./Logo.jsx";

// Las rutas que empiezan con "/" usan el router; los anclas y mailto siguen siendo enlaces normales.
const columns = [
  { title: "Producto", links: [["Panel del taller", "/taller"], ["Agentes", "#agentes"], ["Integraciones", "#plataforma"]] },
  { title: "Recursos", links: [["Centro de ayuda", "/ayuda"], ["Seguridad", "#seguridad"], ["Estado del sistema", "/ayuda#estado"]] },
  { title: "Contacto", links: [["Solicitar demo", "#demo"], ["hola@techfix.ai", "mailto:hola@techfix.ai"], ["Soporte técnico", "/ayuda"]] },
];

function FooterLink({ href, children }) {
  return href.startsWith("/") ? <Link to={href}>{children}</Link> : <a href={href}>{children}</a>;
}

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer__top">
          <div className="footer__brand">
            <Logo />
            <p>
              Plataforma inteligente de servicio técnico para talleres que necesitan operar con más
              velocidad, precisión y confianza.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.title} className="footer__col">
              <h4>{col.title}</h4>
              <ul>
                {col.links.map(([label, href]) => (
                  <li key={label}><FooterLink href={href}>{label}</FooterLink></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="footer__bottom">
          <p>© 2026 TechFix.AI Inc. Todos los derechos reservados.</p>
          <nav aria-label="Legal">
            <Link to="/ayuda#legal">Privacidad</Link>
            <Link to="/ayuda#legal">Términos</Link>
            <Link to="/ayuda#legal">Certificaciones</Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
