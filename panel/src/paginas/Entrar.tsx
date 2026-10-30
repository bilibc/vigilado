import { FormEvent, useState } from "react";
import { api } from "../api";

export default function Entrar({ alEntrar }: { alEntrar: (token: string) => void }) {
  const [email, setEmail] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError("");
    try {
      const r = await api<{ token: string }>("/sesion", { method: "POST", body: JSON.stringify({ email, clave }) });
      alEntrar(r.token);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="entrar">
      <form onSubmit={enviar} className="tarjeta-entrar">
        <div className="marca grande">
          <svg viewBox="0 0 32 32" width="34" height="34" aria-hidden>
            <rect width="32" height="32" rx="8" fill="currentColor" />
            <circle cx="16" cy="16" r="7" fill="none" stroke="var(--fondo)" strokeWidth="2.5" />
            <circle cx="16" cy="16" r="2.6" fill="var(--senal)" />
          </svg>
          <span>Vigilado</span>
        </div>
        <p className="sub">Tus cámaras, revisadas por ti. Solo lo que importa.</p>
        <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required /></label>
        <label>Contraseña<input type="password" value={clave} onChange={(e) => setClave(e.target.value)} autoComplete="current-password" required /></label>
        {error && <div className="error">{error}</div>}
        <button className="primario" disabled={enviando}>{enviando ? "Entrando…" : "Entrar"}</button>
      </form>
    </div>
  );
}
