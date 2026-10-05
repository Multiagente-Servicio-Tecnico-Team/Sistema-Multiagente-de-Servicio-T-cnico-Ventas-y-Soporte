import { createContext, useCallback, useContext, useMemo, useReducer } from "react";

/*
 * Estado de demostración en memoria. Los importes se guardan en céntimos (enteros)
 * para evitar errores de coma flotante; los valores provienen de los diseños de Figma.
 */

export const STAFF_STATUSES = [
  "Nuevo",
  "En Revisión Técnica",
  "Esperando Stock",
  "Presupuesto Aprobado",
  "Listo para Retiro",
  "Entregado",
];

export const TICKET_CATEGORIES = ["Reparación", "Venta", "Soporte"];

export const PART_CATEGORIES = [
  "Memorias RAM",
  "Almacenamiento SSD / HDD",
  "Pantallas",
  "Baterías",
  "Cargadores",
];

export function formatPEN(cents) {
  if (cents === null || cents === undefined) return "Por cotizar";
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const soles = Math.floor(abs / 100).toLocaleString("en-US");
  const cts = String(abs % 100).padStart(2, "0");
  return `${sign}S/. ${soles}.${cts}`;
}

/** Convierte "114.75" en 11475. Devuelve null si el texto no es un importe válido. */
export function parseMoney(text) {
  const clean = String(text).trim().replace(/,/g, "");
  const match = /^(\d{1,7})(?:\.(\d{1,2}))?$/.exec(clean);
  if (!match) return null;
  return Number(match[1]) * 100 + Number((match[2] || "0").padEnd(2, "0"));
}

export function centsToInput(cents) {
  if (cents === null || cents === undefined) return "";
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, "0")}`;
}

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const staffTickets = [
  { id: "TCK-2041", date: "24/10/24", client: "Martín Gómez", phone: "+51 984 219 920", email: "martin.gomez@empresa.pe", device: "MacBook Pro 14\" M2 Max (2023)", issue: "Pantalla en negro y fallo de lectura en almacenamiento persistente tras actualización de sistema.", category: "Reparación", budget: 39500, status: "En Revisión Técnica", origin: "Bot", payment: "Pendiente de aprobación", advance: null, method: null },
  { id: "TCK-2040", date: "23/10/24", client: "Valeria Lozano", phone: "+51 916 310 844", email: "", device: "iPhone 15 Pro Max", issue: "Reemplazo Pantalla OLED + Lidar", category: "Reparación", budget: 31200, status: "Esperando Stock", origin: "Presencial", payment: "Pendiente", advance: null, method: null },
  { id: "TCK-2039", date: "22/10/24", client: "Diego Rossi", phone: "+51 915 092 133", email: "", device: "Armado PC Workstation Threadripper", issue: "Setup 128GB RAM + RTX 4090 24GB", category: "Venta", budget: 425000, status: "Presupuesto Aprobado", origin: "Bot", payment: "Aprobado", advance: null, method: null },
  { id: "TCK-2038", date: "21/10/24", client: "Camila Peralta", phone: "+51 913 289 775", email: "", device: "Dell XPS 15 9520", issue: "Limpieza térmica, repaste PTM7950 y BIOS", category: "Soporte", budget: 4800, status: "Listo para Retiro", origin: "Bot", payment: "Aprobado", advance: null, method: null },
  { id: "TCK-2037", date: "24/10/24", client: "Esteban Bauer", phone: "+51 991 244 802", email: "", device: "PlayStation 5 Slim", issue: "Lector óptico atascado / Error CE-108255-1", category: "Reparación", budget: 6500, status: "Nuevo", origin: "Presencial", payment: "Pendiente", advance: null, method: null },
  { id: "TCK-2036", date: "20/10/24", client: "Romina Navarro", phone: "+51 918 820 192", email: "", device: "iPad Air 5th Gen (M1)", issue: "Batería degradada + puerto Type-C", category: "Soporte", budget: 9200, status: "Entregado", origin: "Presencial", payment: "Pagado", advance: null, method: null },
];

const clientTickets = [
  { id: "TCK-2052", when: "Ayer a las 17:40", kind: "Reparación", device: "Asus ROG Strix G15", icon: "laptop", summary: "Falla de ventilador GPU, ruido anormal y apagado térmico por precaución.", note: "Presupuesto emitido por Diagnóstico IA · Pendiente de visto bueno", status: "approval", lines: [], total: 16000 },
  { id: "TCK-2041", when: "24/10/24 · 10:15 AM", kind: "Reparación de hardware", device: "MacBook Pro 14\" M2 Max (2023)", icon: "monitor", summary: "Pantalla en negro y fallo de lectura en almacenamiento persistente tras actualización de sistema.", status: "approval", lines: [
    { label: "Mano de obra especializada (Triage & Microelectrónica)", amount: 4500 },
    { label: "SSD NVMe 1TB Samsung 980 (Repuesto Original OEM)", amount: 35000 },
  ], total: 39500 },
  { id: "TCK-1988", when: "18/10/24 · 14:02", kind: "Venta de repuesto", device: "Memoria RAM DDR4 16GB Kingston Fury Beast 3200MHz (2 unidades)", icon: "chip", summary: "Adquisición directa de componentes para retiro presencial inmediato.", pickup: "Retiro en Sede Central — Locker Inteligente #4", status: "ready", lines: [], total: 23000 },
  { id: "TCK-1850", when: "05/10/24 · Cerrado", kind: "Soporte técnico", device: "Lenovo ThinkPad T14", icon: "done", summary: "Mantenimiento térmico, limpieza interna ultrasónica y actualización de firmware BIOS completados satisfactoriamente.", status: "done", lines: [], total: 8000 },
];

const parts = [
  { sku: "SSD-NVME-2TB-KC", name: "SSD NVMe M.2 2TB Kingston KC3000 PCIe 4.0", category: "Almacenamiento SSD / HDD", compat: "Laptops Dell XPS / ThinkPad T-Series / Gaming", stock: 34, min: 5, price: 11475, icon: "chip" },
  { sku: "LCD-156-FHD144-40P", name: "Display FHD 15.6\" IPS 144Hz 40-Pin eDP Slim", category: "Pantallas", compat: "Acer Nitro 5 / ASUS TUF Gaming / HP Omen", stock: 2, min: 5, price: 9800, icon: "monitor" },
  { sku: "BAT-APL-A2337", name: "Batería A2337 Original OEM 49.9Wh", category: "Baterías", compat: "Apple MacBook Air M1 (2020)", stock: 19, min: 5, price: 8010, icon: "battery" },
  { sku: "RAM-CRU-16G-D5", name: "RAM SODIMM Crucial 16GB DDR5 4800MHz CL40", category: "Memorias RAM", compat: "Laptops Lenovo Legion / Dell Latitude 5530", stock: 62, min: 10, price: 5200, icon: "ram" },
];

// Solo se guarda rol, nombre y correo; nunca contraseñas.
const SESSION_KEY = "techfix.session";

function readSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeSession(session) {
  try {
    if (session) sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* almacenamiento no disponible: la sesión vive solo en memoria */
  }
}

function today() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${String(d.getFullYear()).slice(-2)}`;
}

function reducer(state, action) {
  switch (action.type) {
    case "login":
      return { ...state, session: action.session, signedOut: false };
    case "logout":
      // signedOut distingue un cierre de sesión voluntario de un acceso sin sesión.
      return { ...state, session: null, signedOut: true };
    case "clearSignedOut":
      return state.signedOut ? { ...state, signedOut: false } : state;
    case "createTicket": {
      const next = Math.max(...state.staffTickets.map((t) => Number(t.id.split("-")[1]))) + 1;
      const ticket = { ...action.ticket, id: `TCK-${next}`, date: today(), status: "Nuevo", origin: "Presencial", budget: null };
      return { ...state, staffTickets: [ticket, ...state.staffTickets] };
    }
    case "updateTicket":
      return {
        ...state,
        staffTickets: state.staffTickets.map((t) => (t.id === action.id ? { ...t, ...action.changes } : t)),
      };
    case "createConsultation": {
      // Consulta nueva desde el chat: crea el ticket del cliente y lo envía a la cola del taller.
      const ids = [...state.staffTickets, ...state.clientTickets].map((t) => Number(t.id.split("-")[1]));
      const id = action.id || `TCK-${Math.max(...ids) + 1}`;
      const { summary, client } = action;
      const device = action.device || "Equipo por confirmar";
      return {
        ...state,
        lastConsultation: id,
        clientTickets: [
          { id, when: "Hoy", kind: "Consulta", device, icon: "laptop", summary, status: "received", lines: [], total: null },
          ...state.clientTickets,
        ],
        staffTickets: [
          { id, date: today(), client: client.name, phone: "Por confirmar", email: client.email, device, issue: summary, category: "Reparación", budget: null, status: "Nuevo", origin: "Bot", payment: "Pendiente", advance: null, method: null },
          ...state.staffTickets,
        ],
      };
    }
    case "approveBudget":
      return {
        ...state,
        clientTickets: state.clientTickets.map((t) => (t.id === action.id ? { ...t, status: "workshop" } : t)),
        staffTickets: state.staffTickets.map((t) => (t.id === action.id ? { ...t, payment: "Aprobado por el cliente" } : t)),
      };
    case "savePart": {
      const exists = state.parts.some((p) => p.sku === action.part.sku);
      return {
        ...state,
        parts: exists
          ? state.parts.map((p) => (p.sku === action.part.sku ? { ...p, ...action.part } : p))
          : [{ icon: "chip", ...action.part }, ...state.parts],
      };
    }
    default:
      return state;
  }
}

const StoreContext = createContext(null);

export function StoreProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, null, () => ({ staffTickets, clientTickets, parts, session: readSession() }));

  const login = useCallback((session) => {
    writeSession(session);
    dispatch({ type: "login", session });
  }, []);

  const logout = useCallback(() => {
    writeSession(null);
    dispatch({ type: "logout" });
  }, []);

  const value = useMemo(() => ({ ...state, dispatch, login, logout }), [state, login, logout]);
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore debe usarse dentro de StoreProvider");
  return ctx;
}
