import { CalendarDays, Mail } from "lucide-react";
import Eyebrow from "./Eyebrow.jsx";

export default function CallToAction() {
  return (
    <section className="cta" id="demo">
      <div className="container cta__inner">
        <Eyebrow center tone="cyan">Tu operación puede empezar hoy</Eyebrow>
        <h2 className="cta__title">Convierte cada ticket en un flujo claro, coordinado y medible</h2>
        <p className="cta__lead">
          Conoce cómo TechFix.AI se adapta a tus reglas, herramientas y equipo. Diseñamos contigo
          el primer flujo y medimos el impacto desde la operación piloto.
        </p>
        <div className="hero__ctas">
          <a href="mailto:hola@techfix.ai?subject=Solicitud%20de%20demo" className="btn btn--primary btn--lg">
            <CalendarDays size={18} aria-hidden="true" /> Solicitar una demo
          </a>
          <a href="mailto:hola@techfix.ai?subject=Consulta%20de%20producto" className="btn btn--outline-dark btn--lg">
            <Mail size={18} aria-hidden="true" /> Hablar con producto
          </a>
        </div>
        <p className="cta__note"><span className="eyebrow__dot" aria-hidden="true" />Respuesta de un especialista en menos de 1 día hábil</p>
      </div>
    </section>
  );
}
