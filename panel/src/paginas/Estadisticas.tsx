import { useEffect, useState } from "react";
import { Estadisticas, api } from "../api";
import type { Evento } from "../main";

export default function Resumen({ ultimo }: { ultimo: Evento | null }) {
  const [e, setE] = useState<Estadisticas | null>(null);
  useEffect(() => { api<Estadisticas>("/estadisticas?dias=14").then(setE); }, [ultimo]);
  if (!e) return <div className="pagina"><div className="vacio">Cargando…</div></div>;
  const max = Math.max(1, ...e.por_dia.map((d) => d.alertas));

  return (
    <div className="pagina">
      <header className="cabecera"><h1>Resumen</h1><span className="resumen">Últimos 14 días</span></header>
      <div className="kpis">
        <div className="kpi"><b>{e.total}</b><span>alertas</span></div>
        <div className="kpi"><b>{e.por_estado["confirmada"] ?? 0}</b><span>incidentes confirmados</span></div>
        <div className="kpi"><b>{e.tasa_descartadas === null ? "—" : `${Math.round(e.tasa_descartadas * 100)} %`}</b><span>falsas alarmas</span></div>
      </div>
      <section className="bloque">
        <h2>Alertas por día</h2>
        <div className="barras">
          {e.por_dia.map((d) => (
            <div key={d.dia} className="barra" title={`${d.alertas} alertas`}>
              <div style={{ height: `${(d.alertas / max) * 100}%` }} />
              <span>{new Date(d.dia).getDate()}</span>
            </div>
          ))}
        </div>
      </section>
      {e.por_camara.length > 0 && (
        <section className="bloque">
          <h2>Dónde hay más alertas</h2>
          <ul className="ranking">
            {e.por_camara.slice(0, 3).map((c) => (
              <li key={c.camara}><span>{c.camara}</span><div><i style={{ width: `${(c.alertas / e.por_camara[0].alertas) * 100}%` }} /></div><b>{c.alertas}</b></li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
