import { useEffect, useState } from "react";
import { Camara, Usuario, api, haceCuanto } from "../api";
import type { Evento } from "../main";

export default function Camaras({ yo, ultimo }: { yo: Usuario; ultimo: Evento | null }) {
  const [camaras, setCamaras] = useState<Camara[]>([]);
  const cargar = () => api<Camara[]>("/camaras").then(setCamaras);
  useEffect(() => { cargar(); }, []);
  useEffect(() => { if (ultimo?.tipo === "camaras") cargar(); }, [ultimo]);
  useEffect(() => { const t = setInterval(cargar, 30000); return () => clearInterval(t); }, []);

  const porTienda = camaras.reduce<Record<string, Camara[]>>((acc, c) => ((acc[c.tienda] ||= []).push(c), acc), {});
  const enLinea = camaras.filter((c) => c.en_linea).length;

  async function alternar(c: Camara) {
    const n = await api<Camara>(`/camaras/${c.id}`, { method: "PATCH", body: JSON.stringify({ activa: !c.activa }) });
    setCamaras((l) => l.map((x) => (x.id === n.id ? n : x)));
  }

  return (
    <div className="pagina">
      <header className="cabecera">
        <h1>Cámaras</h1>
        <span className="resumen">{enLinea} de {camaras.length} en línea</span>
      </header>
      {camaras.length === 0 && (
        <div className="vacio">
          <b>Aún no hay cámaras</b>
          <span>Aparecen solas en cuanto el equipo de la tienda empieza a enviar su estado.</span>
        </div>
      )}
      {Object.entries(porTienda).map(([tienda, lista]) => (
        <section key={tienda} className="bloque">
          <h2>{tienda}</h2>
          <div className="rejilla-camaras">
            {lista.map((c) => (
              <div key={c.id} className={`camara ${c.activa ? "" : "inactiva"}`}>
                <div className="miniatura">
                  <span className={`estado-cam ${c.en_linea ? "si" : "no"}`}><i />{c.en_linea ? "En línea" : "Sin señal"}</span>
                </div>
                <div className="info">
                  <b>{c.nombre}</b>
                  <span>{c.ubicacion || c.codigo}</span>
                  <span className="tenue">
                    {c.en_linea ? `${c.fps.toFixed(1)} fps analizados` : c.ultimo_latido ? `Último aviso ${haceCuanto(c.ultimo_latido)}` : "Nunca conectada"}
                  </span>
                </div>
                {yo.rol === "propietario" && (
                  <button className="enlace" onClick={() => alternar(c)}>{c.activa ? "Desactivar" : "Activar"}</button>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}
      <p className="nota-rol">Por privacidad, el vídeo en directo no sale de la tienda: aquí solo ves el estado y, en Alertas, los clips de cada aviso.</p>
    </div>
  );
}
