import { useEffect, useState } from "react";
import { api, fecha } from "../api";

type Fila = { momento: string; usuario: string; accion: string; objeto: string; detalle: string; ip: string };
const ACCIONES: Record<string, string> = {
  inicio_sesion: "Inicio de sesión", ver_clip: "Ha visto un clip", cambiar_alerta: "Revisión de alerta",
  crear_usuario: "Usuario creado", crear_tienda: "Tienda creada", crear_camara: "Cámara creada",
  cambiar_camara: "Cámara modificada", crear_equipo: "Equipo dado de alta", clip_caducado: "Clip borrado (plazo de conservación)",
};

export default function Registro() {
  const [filas, setFilas] = useState<Fila[]>([]);
  useEffect(() => { api<Fila[]>("/registro").then(setFilas); }, []);
  return (
    <div className="pagina">
      <header className="cabecera"><h1>Registro de accesos</h1><span className="resumen">Quién ha visto qué y cuándo</span></header>
      <table className="tabla">
        <thead><tr><th>Cuándo</th><th>Quién</th><th>Acción</th><th>Detalle</th><th>IP</th></tr></thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={i}><td>{fecha(f.momento)}</td><td>{f.usuario}</td><td>{ACCIONES[f.accion] ?? f.accion}</td>
              <td className="tenue">{f.detalle || f.objeto}</td><td className="tenue">{f.ip}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
