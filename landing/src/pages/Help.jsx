import { Link } from "react-router-dom";
import { Activity, LifeBuoy, Mail, MessageSquareText, Scale } from "lucide-react";

/** Pantalla creada: los diseños enlazan "Soporte Técnico" y "Preguntas Frecuentes" pero no los incluían. */
const faqs = [
  {
    q: "¿Cómo consulto el estado de mi reparación?",
    a: "Ingresa al portal de clientes y abre Mis Tickets. Cada ticket muestra su estado actual: esperando aprobación, en diagnóstico, listo para retiro o completado.",
  },
  {
    q: "¿Cómo apruebo un presupuesto?",
    a: "Desde Mis Tickets o desde el chat con el asistente IA. El presupuesto detalla mano de obra y repuestos; al aprobarlo se registra la fecha y hora y el taller inicia la reparación.",
  },
  {
    q: "¿El asistente IA puede cambiar el precio de mi presupuesto?",
    a: "No. Los importes provienen del catálogo y del inventario del taller. Las excepciones las revisa una persona del equipo antes de comunicarse contigo.",
  },
  {
    q: "Olvidé mi contraseña, ¿qué hago?",
    a: "Usa la opción ¿Olvidaste tu contraseña? en la pantalla de acceso. Recibirás un enlace temporal válido durante 15 minutos.",
  },
  {
    q: "¿Para qué usan mi número de teléfono?",
    a: "Solo para avisos de retiro y actualizaciones del triage de tus equipos.",
  },
];

export default function Help() {
  return (
    <div className="help">
      <div className="auth-card auth-card--wide auth-card--left">
        <div className="auth-card__body">
          <span className="badge"><LifeBuoy size={14} aria-hidden="true" />Soporte técnico</span>
          <h1 className="auth-title">¿En qué podemos ayudarte?</h1>
          <p className="auth-sub">Elige el canal que prefieras. El asistente IA atiende tus consultas sobre tickets y presupuestos en todo momento.</p>
          <div className="help-cards">
            <Link to="/portal/asistente" className="help-card">
              <MessageSquareText size={20} aria-hidden="true" />
              <strong>Chat con el asistente IA</strong>
              <span>Diagnóstico y presupuestos</span>
            </Link>
            <a href="mailto:hola@techfix.ai" className="help-card">
              <Mail size={20} aria-hidden="true" />
              <strong>hola@techfix.ai</strong>
              <span>Respuesta en menos de 1 día hábil</span>
            </a>
          </div>
        </div>
      </div>

      <section id="faq" className="auth-card auth-card--wide auth-card--left">
        <div className="auth-card__body">
          <h2 className="section-title">Preguntas Frecuentes</h2>
          <div className="faq">
            {faqs.map((f) => (
              <details key={f.q}>
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section id="estado" className="auth-card auth-card--wide auth-card--left">
        <div className="auth-card__body">
          <h2 className="section-title"><Activity size={18} aria-hidden="true" /> Estado del sistema</h2>
          <p className="auth-sub">Esta versión es un entorno de demostración: los datos se guardan solo en tu navegador mientras la pestaña está abierta.</p>
        </div>
      </section>

      <section id="legal" className="auth-card auth-card--wide auth-card--left">
        <div className="auth-card__body">
          <h2 className="section-title"><Scale size={18} aria-hidden="true" /> Términos, privacidad y certificaciones</h2>
          <p className="auth-sub">Los documentos legales definitivos están pendientes de publicación. Para consultas escribe a <a className="link" href="mailto:hola@techfix.ai">hola@techfix.ai</a>.</p>
        </div>
      </section>
    </div>
  );
}
