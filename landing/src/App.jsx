import { Route, Routes } from "react-router-dom";
import { RequireRole, ScrollManager } from "./components/ui.jsx";
import AuthLayout from "./layouts/AuthLayout.jsx";
import PortalLayout from "./layouts/PortalLayout.jsx";
import Landing from "./pages/Landing.jsx";
import Help from "./pages/Help.jsx";
import NotFound from "./pages/NotFound.jsx";
import Login from "./pages/portal/Login.jsx";
import Register from "./pages/portal/Register.jsx";
import Recover from "./pages/portal/Recover.jsx";
import Tickets from "./pages/portal/Tickets.jsx";
import Assistant from "./pages/portal/Assistant.jsx";

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
          <Route path="/ayuda" element={<Help />} />
          <Route path="*" element={<NotFound />} />
        </Route>

        <Route element={<RequireRole role="client"><PortalLayout /></RequireRole>}>
          <Route path="/portal" element={<Tickets />} />
          <Route path="/portal/tickets" element={<Tickets />} />
          <Route path="/portal/asistente" element={<Assistant />} />
        </Route>
      </Routes>
    </>
  );
}
