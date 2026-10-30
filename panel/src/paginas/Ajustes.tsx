import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { dia } from "../textos";

type U = { id: string; email: string; nombre: string; rol: string };
type Fila = { momento: string; usuario: string; accion: string };
const ROLES: Record<string, string> = { propietario: "Propietario", encargado: "Encargado", lectura: "Solo ver" };
const ACCIONES: Record<string, string> = {
  inicio_sesion: "Entró en el panel", ver_clip: "Vio un vídeo", cambiar_alerta: "Revisó una alerta", crear_usuario: "Añadió un usuario",
  clip_caducado: "Vídeo borrado tras 30 días",
};

export default function Ajustes() {
  const [usuarios, setUsuarios] = useState<U[]>([]);
  const [registro, setRegistro] = useState<Fila[]>([]);
  const [form, setForm] = useState({ nombre: "", email: "", clave: "", rol: "encargado" });
  const [abierto, setAbierto] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { api<U[]>("/usuarios").then(setUsuarios); api<Fila[]>("/registro").then(setRegistro); }, []);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const n = await api<U>("/usuarios", { method: "POST", body: JSON.stringify(form) });
      setUsuarios((l) => [...l, n]);
      setForm({ nombre: "", email: "", clave: "", rol: "encargado" });
      setAbierto(false);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="pagina">
      <header className="cabecera"><h1>Ajustes</h1></header>
      <section className="bloque">
        <div className="titulo-bloque"><h2>Quién tiene acceso</h2>{!abierto && <button onClick={() => setAbierto(true)}>Añadir persona</button>}</div>
        {abierto && (
          <form className="formulario" onSubmit={crear}>
            <input id="u-nombre" placeholder="Nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
            <input id="u-email" placeholder="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            <input id="u-clave" placeholder="Contraseña (mínimo 10 caracteres)" type="password" minLength={10} value={form.clave}
                   onChange={(e) => setForm({ ...form, clave: e.target.value })} required />
            <select id="u-rol" value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}>
              <option value="encargado">Encargado: revisa alertas</option>
              <option value="lectura">Solo ver</option>
              <option value="propietario">Propietario: todo</option>
            </select>
            {error && <div className="error">{error}</div>}
            <div className="acciones"><button className="primario">Añadir</button><button type="button" onClick={() => setAbierto(false)}>Cancelar</button></div>
          </form>
        )}
        <ul className="filas">
          {usuarios.map((u) => <li key={u.id}><b>{u.nombre}</b><span className="tenue">{u.email}</span><span className="etiqueta">{ROLES[u.rol] ?? u.rol}</span></li>)}
        </ul>
      </section>
      <section className="bloque">
        <h2>Actividad reciente</h2>
        <ul className="filas">
          {registro.slice(0, 15).map((f, i) => (
            <li key={i}><span className="tenue hora">{dia(f.momento)}</span><b>{ACCIONES[f.accion] ?? f.accion}</b><span className="tenue">{f.usuario}</span></li>
          ))}
        </ul>
      </section>
    </div>
  );
}
