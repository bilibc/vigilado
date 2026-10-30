import { useEffect, useState } from "react";
import { Estadisticas, api } from "../api";
import type { Evento } from "../main";

export default function EstadisticasPagina({ ultimo }: { ultimo: Evento | null }) {
  const [e, setE] = useState<Estadisticas | null>(null);
  useEffect(() => { api<Estadisticas>("/estadisticas?dias=14").then(setE); }, [ultimo]);
  if (!e) return <div className="pagina"><div className="vacio">Cargando…</div></div>;
  const max = Math.max(1, ...e.por_dia.map((d) => d.alertas));
  const confirmadas = e.por_estado["confirmada"] ?? 0;

  return (
    <div className="pagina">
      <header className="cabecera"><h1>Estadísticas</h1><span className="resumen">Últimos 14 días</span></header>
      <div className="kpis">
        <div className="kpi"><span>Alertas</span><b>{e.total}</b></div>
        <div className="kpi"><span>Pendientes de revisar</span><b>{e.pendientes}</b></div>
        <div className="kpi"><span>Incidentes confirmados</span><b>{confirmadas}</b></div>
        <div className="kpi"><span>Falsas alarmas</span><b>{e.tasa_descartadas === null ? "—" : `${Math.round(e.tasa_descartadas * 100)} %`}</b>
          <small>de las alertas revisadas</small></div>
      </div>
      <section className="bloque">
        <h2>Alertas por día</h2>
        <div className="barras">
          {e.por_dia.map((d) => (
            <div key={d.dia} className="barra" title={`${d.dia}: ${d.alertas}`}>
              <div style={{ height: `${(d.alertas / max) * 100}%` }} />
              <span>{new Date(d.dia).toLocaleDateString("es-ES", { day: "numeric" })}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="bloque">
        <h2>Por cámara</h2>
        {e.por_camara.length === 0 ? <div className="vacio">Sin datos todavía.</div> : (
          <ul className="ranking">
            {e.por_camara.map((c) => (
              <li key={c.camara}><span>{c.camara}</span><div><i style={{ width: `${(c.alertas / e.por_camara[0].alertas) * 100}%` }} /></div><b>{c.alertas}</b></li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
