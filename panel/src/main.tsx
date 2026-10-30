import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, MemoryRouter, NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { Alerta, DEMO, Usuario, api, escuchar, sesion } from "./api";
import Alertas from "./paginas/Alertas";
import Camaras from "./paginas/Camaras";
import Entrar from "./paginas/Entrar";
import EstadisticasPagina from "./paginas/Estadisticas";
import Registro from "./paginas/Registro";
import Usuarios from "./paginas/Usuarios";
import "./estilos.css";

export type Evento = { tipo: string; nueva?: boolean; alerta?: Alerta };

function Marca() {
  return (
    <div className="marca">
      <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden>
        <rect width="32" height="32" rx="8" fill="currentColor" />
        <circle cx="16" cy="16" r="7" fill="none" stroke="var(--fondo)" strokeWidth="2.5" />
        <circle cx="16" cy="16" r="2.6" fill="var(--senal)" />
      </svg>
      <span>Vigilado</span>
    </div>
  );
}

function App() {
  const [yo, setYo] = useState<Usuario | null>(null);
  const [conectado, setConectado] = useState(false);
  const [ultimo, setUltimo] = useState<Evento | null>(null);
  const [aviso, setAviso] = useState<Alerta | null>(null);
  const ir = useNavigate();

  useEffect(() => { api<Usuario>("/yo").then(setYo).catch(() => sesion.cerrar()); }, []);
  useEffect(() => {
    return escuchar((msg) => {
      setUltimo({ ...msg });
      if (msg.nueva && msg.alerta) {
        setAviso(msg.alerta);
        setTimeout(() => setAviso(null), 6000);
        try {
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification("Vigilado · revisar", { body: `${msg.alerta.camara.nombre}: ${msg.alerta.titulo}` });
          }
        } catch { /* sin notificaciones del navegador */ }
      }
    }, setConectado);
  }, []);
  useEffect(() => {
    try { if (!DEMO && "Notification" in window && Notification.permission === "default") Notification.requestPermission(); } catch { /* */ }
  }, []);

  if (!yo) return <div className="cargando">Cargando…</div>;
  const propietario = yo.rol === "propietario";
  return (
    <div className={`app ${DEMO ? "con-demo" : ""}`}>
      {DEMO && <div className="banda-demo">Demo con datos de ejemplo · los vídeos son simulaciones con esqueletos · cada ~25 s entra una alerta nueva</div>}
      <aside className="lateral">
        <Marca />
        <nav>
          <NavLink to="/alertas">Alertas</NavLink>
          <NavLink to="/camaras">Cámaras</NavLink>
          <NavLink to="/estadisticas">Estadísticas</NavLink>
          {propietario && <NavLink to="/registro">Registro de accesos</NavLink>}
          {propietario && <NavLink to="/usuarios">Usuarios</NavLink>}
        </nav>
        <div className="pie-lateral">
          <div className={`conexion ${conectado ? "si" : "no"}`}>
            <i />{conectado ? "En directo" : "Reconectando…"}
          </div>
          <div className="quien">
            <strong>{yo.nombre}</strong>
            <span>{yo.rol}</span>
          </div>
          <button className="enlace" onClick={sesion.cerrar}>Cerrar sesión</button>
        </div>
      </aside>
      <main className="contenido">
        <Routes>
          <Route path="/alertas/:id?" element={<Alertas yo={yo} ultimo={ultimo} />} />
          <Route path="/camaras" element={<Camaras yo={yo} ultimo={ultimo} />} />
          <Route path="/estadisticas" element={<EstadisticasPagina ultimo={ultimo} />} />
          {propietario && <Route path="/registro" element={<Registro />} />}
          {propietario && <Route path="/usuarios" element={<Usuarios />} />}
          <Route path="*" element={<Navigate to="/alertas" replace />} />
        </Routes>
      </main>
      {aviso && (
        <button className={`toast p-${aviso.prioridad}`} onClick={() => { ir(`/alertas/${aviso.id}`); setAviso(null); }}>
          <b>Nueva alerta · {aviso.camara.nombre}</b>
          <span>{aviso.titulo}</span>
        </button>
      )}
    </div>
  );
}

function Raiz() {
  const [token, setToken] = useState(sesion.token());
  if (DEMO) return <MemoryRouter initialEntries={["/alertas"]}><App /></MemoryRouter>;
  if (!token) return <Entrar alEntrar={(t) => { sesion.guardar(t); setToken(t); }} />;
  return <BrowserRouter><App /></BrowserRouter>;
}

ReactDOM.createRoot(document.getElementById("raiz")!).render(<React.StrictMode><Raiz /></React.StrictMode>);
