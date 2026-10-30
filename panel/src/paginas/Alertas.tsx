import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alerta, Estado, Usuario, api, enlaceClip } from "../api";
import type { Evento } from "../main";
import { dia, hora, paso, titulo } from "../textos";

const RESULTADO: Record<Estado, string> = { nueva: "Por revisar", revisada: "Revisada", descartada: "Falsa alarma", confirmada: "Incidente confirmado" };

export default function Alertas({ yo, ultimo }: { yo: Usuario; ultimo: Evento | null }) {
  const [todas, setTodas] = useState<Alerta[]>([]);
  const [vista, setVista] = useState<"pendientes" | "historial">("pendientes");
  const [cargando, setCargando] = useState(true);
  const { id } = useParams();
  const ir = useNavigate();

  useEffect(() => { api<Alerta[]>("/alertas").then(setTodas).finally(() => setCargando(false)); }, []);
  useEffect(() => {
    const a = ultimo?.alerta;
    if (a) setTodas((l) => [a, ...l.filter((x) => x.id !== a.id)].sort((x, y) => y.inicio.localeCompare(x.inicio)));
  }, [ultimo]);

  const pendientes = todas.filter((a) => a.estado === "nueva");
  const lista = vista === "pendientes" ? pendientes : todas.filter((a) => a.estado !== "nueva");
  const actual = useMemo(() => todas.find((a) => a.id === id) ?? null, [todas, id]);

  return (
    <div className="alertas">
      <section className="lista">
        <header className="cabecera">
          <h1>Alertas</h1>
          <div className="segmentos">
            <button className={vista === "pendientes" ? "activo" : ""} onClick={() => setVista("pendientes")}>
              Por revisar{pendientes.length > 0 && <span className="contador">{pendientes.length}</span>}
            </button>
            <button className={vista === "historial" ? "activo" : ""} onClick={() => setVista("historial")}>Historial</button>
          </div>
        </header>
        {cargando ? <div className="vacio">Cargando…</div> : lista.length === 0 ? (
          <div className="vacio">
            <b>{vista === "pendientes" ? "Todo revisado" : "Aún no hay historial"}</b>
            <span>{vista === "pendientes" ? "Cuando una cámara vea algo que debas mirar, aparecerá aquí al momento." : ""}</span>
          </div>
        ) : (
          <ul>
            {lista.map((a) => (
              <li key={a.id} className={a.id === id ? "elegida" : ""} onClick={() => ir(`/alertas/${a.id}`)}>
                <span className={`punto p-${a.prioridad}`} />
                <div className="texto">
                  <b>{titulo(a)}</b>
                  <span>{a.camara.nombre} · {dia(a.inicio)}</span>
                </div>
                {vista === "pendientes" ? (a.prioridad === "alta" && <span className="chip p-alta">Urgente</span>)
                  : <span className={`resultado e-${a.estado}`}>{RESULTADO[a.estado]}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="detalle">
        {actual ? <Detalle a={actual} yo={yo} alCambiar={(n) => setTodas((l) => l.map((x) => (x.id === n.id ? n : x)))} />
          : <div className="vacio grande">Elige una alerta para ver el vídeo.</div>}
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
        <div className="migas">{a.camara.nombre} · {a.camara.tienda}</div>
        <h2>{titulo(a)}</h2>
        <div className="meta">
          {a.prioridad === "alta" && <span className="chip p-alta">Urgente</span>}
          <span>{dia(a.inicio)}</span>
          {a.estado !== "nueva" && <span className={`resultado e-${a.estado}`}>{RESULTADO[a.estado]}</span>}
        </div>
      </header>

      <div className="video">
        {a.tiene_clip ? (clip ? <video key={a.id} src={clip} controls autoPlay muted playsInline /> : <div className="sin-clip">Cargando vídeo…</div>)
          : <div className="sin-clip">{a.clip_borrado ? "Vídeo borrado (se guardan 30 días)" : "Preparando el vídeo…"}</div>}
      </div>

      <ol className="pasos">
        {a.pasos.map((p, i) => (
          <li key={i} className={`paso-${p.tipo}`}>
            <span className="icono" />
            <span className="texto">{paso(p)}</span>
            <time>{hora(a.inicio, p.t)}</time>
          </li>
        ))}
      </ol>

      <p className="aviso-revision">Mira el vídeo antes de actuar. El sistema avisa de un gesto, no acusa a nadie.</p>

      {yo.rol !== "lectura" && (
        <div className="revision">
          <textarea id="nota" placeholder="Nota (opcional)" value={nota} onChange={(e) => setNota(e.target.value)} />
          <div className="acciones">
            <button onClick={() => marcar("descartada")} disabled={guardando} className={a.estado === "descartada" ? "elegido" : ""}>Falsa alarma</button>
            <button className={`peligro ${a.estado === "confirmada" ? "elegido" : ""}`} onClick={() => marcar("confirmada")} disabled={guardando}>
              Confirmar incidente
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
