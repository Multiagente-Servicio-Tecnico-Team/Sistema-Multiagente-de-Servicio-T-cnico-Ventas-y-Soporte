import { Route, Routes } from "react-router-dom";
import { RequireRole, ScrollManager } from "./components/ui.jsx";
import AuthLayout from "./layouts/AuthLayout.jsx";
import PortalLayout from "./layouts/PortalLayout.jsx";
import StaffLayout from "./layouts/StaffLayout.jsx";
import Landing from "./pages/Landing.jsx";
import Help from "./pages/Help.jsx";
import NotFound from "./pages/NotFound.jsx";
import Login from "./pages/portal/Login.jsx";
import Register from "./pages/portal/Register.jsx";
import Recover from "./pages/portal/Recover.jsx";
import Reset from "./pages/portal/Reset.jsx";
import Tickets from "./pages/portal/Tickets.jsx";
import Assistant from "./pages/portal/Assistant.jsx";
import StaffLogin from "./pages/staff/StaffLogin.jsx";
import Workshop from "./pages/staff/Workshop.jsx";
import TicketDetail from "./pages/staff/TicketDetail.jsx";
import NewTicket from "./pages/staff/NewTicket.jsx";
import Inventory from "./pages/staff/Inventory.jsx";
import PartForm from "./pages/staff/PartForm.jsx";

export default function App() {
  return (
    <>
      <ScrollManager />
      <Routes>
        <Route path="/" element={<Landing />} />

        <Route element={<AuthLayout />}>
          <Route path="/portal/acceso" element={<Login />} />
          <Route path="/portal/registro" element={<Register />} />
          <Route path="/portal/recuperar" element={<Recover />} />
          <Route path="/portal/restablecer" element={<Reset />} />
          <Route path="/taller/acceso" element={<StaffLogin />} />
          <Route path="/ayuda" element={<Help />} />
          <Route path="*" element={<NotFound />} />
        </Route>

        <Route element={<RequireRole role="client"><PortalLayout /></RequireRole>}>
          <Route path="/portal" element={<Tickets />} />
          <Route path="/portal/tickets" element={<Tickets />} />
          <Route path="/portal/asistente" element={<Assistant />} />
        </Route>

        <Route element={<RequireRole role="staff"><StaffLayout /></RequireRole>}>
          <Route path="/taller" element={<Workshop />} />
          <Route path="/taller/tickets/nuevo" element={<NewTicket />} />
          <Route path="/taller/tickets/:id" element={<TicketDetail />} />
          <Route path="/taller/inventario" element={<Inventory />} />
          <Route path="/taller/inventario/nuevo" element={<PartForm />} />
          <Route path="/taller/inventario/:sku/editar" element={<PartForm />} />
        </Route>
      </Routes>
    </>
  );
}
