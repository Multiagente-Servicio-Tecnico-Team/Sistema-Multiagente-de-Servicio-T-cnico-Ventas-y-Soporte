import { Route, Routes } from "react-router-dom";
import { ScrollManager } from "./components/ui.jsx";
import AuthLayout from "./layouts/AuthLayout.jsx";
import Landing from "./pages/Landing.jsx";
import NotFound from "./pages/NotFound.jsx";
import Login from "./pages/portal/Login.jsx";
import Register from "./pages/portal/Register.jsx";

export default function App() {
  return (
    <>
      <ScrollManager />
      <Routes>
        <Route path="/" element={<Landing />} />

        <Route element={<AuthLayout />}>
          <Route path="/portal/acceso" element={<Login />} />
          <Route path="/portal/registro" element={<Register />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </>
  );
}
