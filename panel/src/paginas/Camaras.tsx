import { useEffect, useState } from "react";
import { Camara, api, haceCuanto } from "../api";
import type { Evento } from "../main";

export default function Camaras({ ultimo }: { ultimo: Evento | null }) {
  const [camaras, setCamaras] = useState<Camara[]>([]);
  const cargar = () => api<Camara[]>("/camaras").then(setCamaras);
  useEffect(() => { cargar(); }, []);
  useEffect(() => { if (ultimo?.tipo === "camaras") cargar(); }, [ultimo]);
  useEffect(() => { const t = setInterval(cargar, 30000); return () => clearInterval(t); }, []);

  const activas = camaras.filter((c) => c.activa);
  const caidas = activas.filter((c) => !c.en_linea);
  const porTienda = activas.reduce<Record<string, Camara[]>>((acc, c) => ((acc[c.tienda] ||= []).push(c), acc), {});

  return (
    <div className="pagina">
      <header className="cabecera"><h1>Cámaras</h1></header>
      <div className={`estado-general ${caidas.length ? "mal" : "bien"}`}>
        {caidas.length === 0 ? "Todas las cámaras funcionan" : `${caidas.length} ${caidas.length === 1 ? "cámara sin señal" : "cámaras sin señal"}`}
      </div>
      {activas.length === 0 && <div className="vacio"><b>Aún no hay cámaras</b><span>Aparecen solas cuando el equipo de la tienda se conecta.</span></div>}
      {Object.entries(porTienda).map(([tienda, lista]) => (
        <section key={tienda} className="bloque">
          <h2>{tienda}</h2>
          <ul className="filas">
            {lista.map((c) => (
              <li key={c.id}>
                <span className={`punto ${c.en_linea ? "ok" : "mal"}`} />
                <b>{c.nombre}</b>
                <span className="tenue">{c.en_linea ? "Funciona" : c.ultimo_latido ? `Sin señal desde ${haceCuanto(c.ultimo_latido)}` : "Nunca conectada"}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
