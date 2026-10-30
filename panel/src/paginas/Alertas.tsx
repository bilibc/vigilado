import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alerta, Estado, Usuario, api, enlaceClip, fecha, haceCuanto } from "../api";
import type { Evento } from "../main";

const FILTROS: { id: string; nombre: string; estado?: Estado }[] = [
  { id: "nueva", nombre: "Pendientes", estado: "nueva" },
  { id: "todas", nombre: "Todas" },
  { id: "confirmada", nombre: "Incidentes", estado: "confirmada" },
  { id: "descartada", nombre: "Descartadas", estado: "descartada" },
];
const NOMBRE_ESTADO: Record<Estado, string> = { nueva: "Pendiente", revisada: "Revisada", descartada: "Descartada", confirmada: "Incidente confirmado" };
const ICONO_PASO: Record<string, string> = { coge: "↗", ocultacion: "●", salida_sin_caja: "→", paso_por_caja: "✓", manipulacion_repetida: "↻" };

export default function Alertas({ yo, ultimo }: { yo: Usuario; ultimo: Evento | null }) {
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [filtro, setFiltro] = useState("nueva");
  const [cargando, setCargando] = useState(true);
  const { id } = useParams();
  const ir = useNavigate();

  const estado = FILTROS.find((f) => f.id === filtro)?.estado;
  useEffect(() => {
    setCargando(true);
    api<Alerta[]>(`/alertas${estado ? `?estado=${estado}` : ""}`).then(setAlertas).finally(() => setCargando(false));
  }, [estado]);

  // Tiempo real: entra o se actualiza sin recargar
  useEffect(() => {
    const a = ultimo?.alerta;
    if (!a) return;
    setAlertas((lista) => {
      const sin = lista.filter((x) => x.id !== a.id);
      if (estado && a.estado !== estado) return sin;
      return [a, ...sin].sort((x, y) => y.inicio.localeCompare(x.inicio));
    });
  }, [ultimo, estado]);

  const elegida = useMemo(() => alertas.find((a) => a.id === id) ?? null, [alertas, id]);
  const [suelta, setSuelta] = useState<Alerta | null>(null);
  useEffect(() => {
    if (id && !alertas.some((a) => a.id === id)) api<Alerta>(`/alertas/${id}`).then(setSuelta).catch(() => setSuelta(null));
  }, [id, alertas]);
  const actual = elegida ?? (suelta?.id === id ? suelta : null);

  return (
    <div className="alertas">
      <section className="lista">
        <header className="cabecera">
          <h1>Alertas</h1>
          <div className="segmentos">
            {FILTROS.map((f) => (
              <button key={f.id} className={filtro === f.id ? "activo" : ""} onClick={() => setFiltro(f.id)}>{f.nombre}</button>
            ))}
          </div>
        </header>
        {cargando ? <div className="vacio">Cargando…</div> : alertas.length === 0 ? (
          <div className="vacio">
            <b>Nada que revisar</b>
            <span>Cuando una cámara detecte un gesto que merezca revisión, aparecerá aquí al instante.</span>
          </div>
        ) : (
          <ul>
            {alertas.map((a) => (
              <li key={a.id} className={a.id === id ? "elegida" : ""} onClick={() => ir(`/alertas/${a.id}`)}>
                <span className={`punto p-${a.prioridad}`} />
                <div className="texto">
                  <b>{a.camara.nombre}</b>
                  <span>{a.titulo}</span>
                </div>
                <div className="lado">
                  <span className={`chip p-${a.prioridad}`}>{a.prioridad}</span>
                  <time>{haceCuanto(a.inicio)}</time>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="detalle">
        {actual ? <Detalle a={actual} yo={yo} alCambiar={(n) => setAlertas((l) => l.map((x) => (x.id === n.id ? n : x)))} />
          : <div className="vacio grande">Elige una alerta para revisarla.</div>}
      </section>
    </div>
  );
}

function Detalle({ a, yo, alCambiar }: { a: Alerta; yo: Usuario; alCambiar: (a: Alerta) => void }) {
  const [nota, setNota] = useState(a.nota);
  const [guardando, setGuardando] = useState(false);
  const [clip, setClip] = useState<string | null>(null);
  useEffect(() => setNota(a.nota), [a.id, a.nota]);
  useEffect(() => {
    setClip(null);
    if (a.tiene_clip) enlaceClip(a.id).then(setClip).catch(() => setClip(null));
  }, [a.id, a.tiene_clip]);
  const puedeRevisar = yo.rol !== "lectura";

  async function marcar(estado: Estado) {
    setGuardando(true);
    try {
      alCambiar(await api<Alerta>(`/alertas/${a.id}`, { method: "PATCH", body: JSON.stringify({ estado, nota }) }));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <article>
      <header className="cabecera-detalle">
        <div>
          <div className="migas">{a.camara.tienda} · {a.camara.nombre}{a.camara.ubicacion ? ` · ${a.camara.ubicacion}` : ""}</div>
          <h2>{a.titulo}</h2>
          <div className="meta">
            <span className={`chip p-${a.prioridad}`}>Prioridad {a.prioridad}</span>
            <span>Confianza {Math.round(a.puntuacion * 100)} %</span>
            <span>{fecha(a.inicio)}</span>
            <span className={`estado e-${a.estado}`}>{NOMBRE_ESTADO[a.estado]}</span>
            {a.simulacion && <span className="chip simulacion">Simulación</span>}
          </div>
        </div>
      </header>

      <div className="video">
        {a.tiene_clip ? (clip ? <video key={a.id} src={clip} controls autoPlay muted playsInline /> : <div className="sin-clip">Cargando vídeo…</div>)
          : <div className="sin-clip">{a.clip_borrado ? "Clip borrado por el plazo de conservación" : "El clip aún se está generando…"}</div>}
      </div>

      <div className="aviso-revision">
        Esto <b>no es una acusación</b>. El sistema ha visto una secuencia de gestos que merece que una persona revise el vídeo.
      </div>

      <h3>Qué ha visto el sistema</h3>
      <ol className="pasos">
        {a.pasos.map((p, i) => (
          <li key={i} className={`paso-${p.tipo}`}>
            <span className="icono">{ICONO_PASO[p.tipo] ?? "•"}</span>
            <span className="texto">{p.texto}</span>
            <time>+{p.t.toFixed(1)} s</time>
          </li>
        ))}
      </ol>

      <h3>Revisión</h3>
      <textarea placeholder="Nota (opcional): qué has visto, qué se ha hecho…" value={nota} onChange={(e) => setNota(e.target.value)}
                disabled={!puedeRevisar} />
      {puedeRevisar ? (
        <div className="acciones">
          <button onClick={() => marcar("descartada")} disabled={guardando}>Descartar · falsa alarma</button>
          <button onClick={() => marcar("revisada")} disabled={guardando}>Marcar como revisada</button>
          <button className="peligro" onClick={() => marcar("confirmada")} disabled={guardando}>Confirmar incidente</button>
        </div>
      ) : <p className="nota-rol">Tu usuario es de solo lectura.</p>}
      {a.revisada_en && <p className="nota-rol">Última revisión: {fecha(a.revisada_en)}</p>}
    </article>
  );
}
