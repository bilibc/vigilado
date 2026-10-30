import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

type U = { id: string; email: string; nombre: string; rol: string; activo: boolean };
const ROLES: Record<string, string> = {
  propietario: "Propietario · todo, incluidos usuarios y registro",
  encargado: "Encargado · revisa alertas y ve clips",
  lectura: "Lectura · solo consulta",
};

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState<U[]>([]);
  const [form, setForm] = useState({ email: "", nombre: "", clave: "", rol: "encargado" });
  const [error, setError] = useState("");
  useEffect(() => { api<U[]>("/usuarios").then(setUsuarios); }, []);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const n = await api<U>("/usuarios", { method: "POST", body: JSON.stringify(form) });
      setUsuarios((l) => [...l, n]);
      setForm({ email: "", nombre: "", clave: "", rol: "encargado" });
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="pagina">
      <header className="cabecera"><h1>Usuarios</h1></header>
      <table className="tabla">
        <thead><tr><th>Nombre</th><th>Email</th><th>Rol</th></tr></thead>
        <tbody>{usuarios.map((u) => <tr key={u.id}><td>{u.nombre}</td><td>{u.email}</td><td>{u.rol}</td></tr>)}</tbody>
      </table>
      <section className="bloque">
        <h2>Añadir usuario</h2>
        <form className="formulario" onSubmit={crear}>
          <input placeholder="Nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
          <input placeholder="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <input placeholder="Contraseña (mín. 10 caracteres)" type="password" minLength={10} value={form.clave}
                 onChange={(e) => setForm({ ...form, clave: e.target.value })} required />
          <select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}>
            {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          {error && <div className="error">{error}</div>}
          <button className="primario">Crear usuario</button>
        </form>
      </section>
    </div>
  );
}
