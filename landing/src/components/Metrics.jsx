import Eyebrow from "./Eyebrow.jsx";

const metrics = [
  { label: "Tiempo de diagnóstico", value: "−38%", note: "De ingreso a cotización lista" },
  { label: "Tickets por coordinador", value: "2.4×", note: "Sin aumentar retrabajo" },
  { label: "Aprobaciones sin llamada", value: "94%", note: "Desde portal o mensajería" },
  { label: "Stock inmovilizado", value: "−27%", note: "Reservas y alertas anticipadas" },
];

export default function Metrics() {
  return (
    <section className="section section--tint metrics-section">
      <div className="container">
        <div className="metrics">
          <div className="metrics__head">
            <div>
              <Eyebrow dot={false} tone="cyan">Valor operativo medible</Eyebrow>
              <h2 className="h2 h2--light">Más capacidad sin perder precisión ni trazabilidad</h2>
            </div>
            <p>
              Resultados de una operación piloto de 90 días en un taller multimarca con 1,200
              tickets mensuales.
            </p>
          </div>
          <div className="metrics__grid">
            {metrics.map(({ label, value, note }) => (
              <div key={label} className="metric">
                <p className="mono-label">{label}</p>
                <p className="metric__value">{value}</p>
                <p className="metric__note">{note}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
