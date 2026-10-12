import { Link } from "react-router-dom";
import { LoginForm } from "../portal/Login.jsx";

/** Pantalla creada para el personal: los diseños solo incluían el acceso del cliente. */
export default function StaffLogin() {
  return (
    <LoginForm
      role="staff"
      badge="Acceso de personal · Taller"
      title="Ingresar al Panel del Taller"
      subtitle="Gestiona la cola de triage, los tickets presenciales y el inventario de repuestos."
      defaultTo="/taller"
      footer={<p>¿Eres cliente? <Link to="/portal/acceso" className="link">Ir al portal de clientes</Link></p>}
    />
  );
}
