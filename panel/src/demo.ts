// Modo demo: el panel real alimentado con datos de ejemplo en memoria (se activa con VITE_DEMO=1).
// No hay API ni cámaras: las alertas, cámaras y estadísticas son inventadas y van marcadas como demo.
import type { Alerta, Camara, Estado, Estadisticas, Paso, Usuario } from "./api";

const AHORA = Date.now();
let semilla = 7;
const azar = () => ((semilla = (semilla * 16807) % 2147483647) / 2147483647);
const elige = <T,>(xs: T[]) => xs[Math.floor(azar() * xs.length)];
const iso = (ms: number) => new Date(ms).toISOString();

const YO: Usuario = { id: "u1", nombre: "Marta Ruiz", email: "marta@perfumerialumen.es", rol: "propietario" };
const USUARIOS = [
  { id: "u1", nombre: "Marta Ruiz", email: "marta@perfumerialumen.es", rol: "propietario", activo: true },
  { id: "u2", nombre: "Javier Gómez", email: "javier@perfumerialumen.es", rol: "encargado", activo: true },
  { id: "u3", nombre: "Lucía Pérez", email: "lucia@perfumerialumen.es", rol: "encargado", activo: true },
  { id: "u4", nombre: "Gestoría Norte", email: "consultas@gestorianorte.es", rol: "lectura", activo: true },
];

const T1 = { id: "t1", nombre: "Lumen · Santander Centro" };
const T2 = { id: "t2", nombre: "Lumen · Valdecilla" };
const CAMARAS: Camara[] = [
  { id: "c1", codigo: "cam-fragancias", nombre: "Lineal de fragancias", ubicacion: "Pasillo 2", activa: true, en_linea: true, fps: 10, tienda_id: T1.id, tienda: T1.nombre, ultimo_latido: iso(AHORA - 4000) },
  { id: "c2", codigo: "cam-maquillaje", nombre: "Maquillaje", ubicacion: "Pasillo 3", activa: true, en_linea: true, fps: 9.8, tienda_id: T1.id, tienda: T1.nombre, ultimo_latido: iso(AHORA - 6000) },
  { id: "c3", codigo: "cam-entrada", nombre: "Entrada", ubicacion: "Puerta principal", activa: true, en_linea: true, fps: 10, tienda_id: T1.id, tienda: T1.nombre, ultimo_latido: iso(AHORA - 3000) },
  { id: "c4", codigo: "cam-caja", nombre: "Caja", ubicacion: "Mostrador", activa: true, en_linea: false, fps: 0, tienda_id: T1.id, tienda: T1.nombre, ultimo_latido: iso(AHORA - 3 * 3600e3) },
  { id: "c5", codigo: "cam-central", nombre: "Pasillo central", ubicacion: "Cosmética", activa: true, en_linea: true, fps: 9.9, tienda_id: T2.id, tienda: T2.nombre, ultimo_latido: iso(AHORA - 5000) },
  { id: "c6", codigo: "cam-entrada-v", nombre: "Entrada", ubicacion: "Puerta", activa: false, en_linea: false, fps: 0, tienda_id: T2.id, tienda: T2.nombre, ultimo_latido: iso(AHORA - 9 * 86400e3) },
];
const CON_ALERTAS = ["c1", "c1", "c1", "c2", "c2", "c5"];
const ESTANTERIA: Record<string, string> = { c1: "Fragancias mujer", c2: "Labiales", c5: "Cremas faciales" };

type Plantilla = { tipo: string; titulo: string; clip: string; pasos: (est: string, mano: string) => Paso[]; prioridad: Alerta["prioridad"]; punt: number };
const PLANTILLAS: Plantilla[] = [
  { tipo: "ocultacion_bolsillo", titulo: "Gesto compatible con ocultación en bolsillo o cintura", clip: "bolsillo", prioridad: "alta", punt: 0.8,
    pasos: (e, m) => [
      { t: 0, tipo: "coge", texto: `Coge en «${e}» (mano ${m})` },
      { t: 1.4, tipo: "ocultacion", texto: `Mano ${m} a bolsillo o cintura durante 0.9 s` },
      { t: 11.8, tipo: "salida_sin_caja", texto: "Se dirige a la salida sin pasar por caja" }] },
  { tipo: "ocultacion_bolsillo", titulo: "Gesto compatible con ocultación en bolsillo o cintura", clip: "manipulacion", prioridad: "media", punt: 0.65,
    pasos: (e, m) => [
      { t: 0, tipo: "coge", texto: `Coge en «${e}» (mano ${m})` },
      { t: 0.8, tipo: "ocultacion", texto: `Mano ${m} a bolsillo o cintura durante 1.0 s` },
      { t: 0.8, tipo: "manipulacion_repetida", texto: "3 productos cogidos en el último minuto" }] },
  { tipo: "ocultacion_ropa", titulo: "Gesto compatible con ocultación bajo la ropa", clip: "ropa", prioridad: "baja", punt: 0.35,
    pasos: (e, m) => [
      { t: 0, tipo: "coge", texto: `Coge en «${e}» (mano ${m})` },
      { t: 1.1, tipo: "ocultacion", texto: `Mano ${m} a bajo la ropa (torso) durante 1.0 s` },
      { t: 4.0, tipo: "paso_por_caja", texto: "Pasa por la zona de caja" }] },
  { tipo: "ocultacion_ropa", titulo: "Gesto compatible con ocultación bajo la ropa", clip: "ropa", prioridad: "alta", punt: 0.85,
    pasos: (e, m) => [
      { t: 0, tipo: "coge", texto: `Coge en «${e}» (mano ${m})` },
      { t: 1.3, tipo: "ocultacion", texto: `Mano ${m} a bajo la ropa (torso) durante 1.4 s` },
      { t: 9.2, tipo: "salida_sin_caja", texto: "Se dirige a la salida sin pasar por caja" }] },
];
const NOTAS: Record<string, string[]> = {
  descartada: ["Era su móvil.", "Lo dejó en la cesta, no se veía bien.", "Clienta habitual, pagó en caja.", "Se rascó; falsa alarma."],
  confirmada: ["Avisado el vigilante, recuperado en la salida.", "Producto no pagado: 2 colonias. Denuncia presentada.", "Recuperado sin incidentes."],
  revisada: ["Revisado, no se aprecia ocultación clara.", ""],
};

function crearAlerta(ms: number, estado: Estado): Alerta & { _clip: string } {
  const p = elige(PLANTILLAS);
  const camId = elige(CON_ALERTAS);
  const cam = CAMARAS.find((c) => c.id === camId)!;
  const mano = elige(["derecha", "izquierda"]);
  return {
    id: Math.floor(azar() * 1e16).toString(16).padStart(14, "0"), tipo: p.tipo, titulo: p.titulo, puntuacion: p.punt, prioridad: p.prioridad,
    inicio: iso(ms), actualizada: iso(ms + 15000), pasos: p.pasos(ESTANTERIA[cam.id], mano), estado,
    nota: estado === "nueva" ? "" : elige(NOTAS[estado] ?? [""]), simulacion: false,
    tiene_clip: true, clip_borrado: false, revisada_en: estado === "nueva" ? null : iso(ms + 9 * 60e3),
    camara: { id: cam.id, nombre: cam.nombre, ubicacion: cam.ubicacion, tienda: cam.tienda, tienda_id: cam.tienda_id }, _clip: p.clip,
  };
}

// 14 días de historia: las antiguas ya revisadas, las de hoy pendientes
const ALERTAS: (Alerta & { _clip: string })[] = [];
for (let d = 13; d >= 0; d--) {
  const n = d === 0 ? 4 : Math.floor(azar() * 4) + (d % 6 === 2 ? 3 : 0);
  for (let i = 0; i < n; i++) {
    const hora = 10 + Math.floor(azar() * 10);
    const ms = AHORA - d * 86400e3 - (d === 0 ? (i + 1) * 47 * 60e3 : (hora - 9) * 3600e3 + azar() * 3600e3);
    const r = azar();
    const estado: Estado = d === 0 ? "nueva" : r < 0.22 ? "descartada" : r < 0.6 ? "confirmada" : r < 0.85 ? "revisada" : d < 3 ? "nueva" : "revisada";
    ALERTAS.push(crearAlerta(ms, estado));
  }
}
ALERTAS.sort((a, b) => b.inicio.localeCompare(a.inicio));

type FilaRegistro = { momento: string; usuario: string; accion: string; objeto: string; detalle: string; ip: string };
const REGISTRO: FilaRegistro[] = [];
for (const a of ALERTAS.filter((x) => x.estado !== "nueva").slice(0, 30)) {
  const quien = elige(USUARIOS.slice(0, 3));
  const t = new Date(a.revisada_en!).getTime();
  REGISTRO.push({ momento: iso(t), usuario: quien.email, accion: "cambiar_alerta", objeto: a.id, detalle: `estado=${a.estado}`, ip: "88.27.114.6" });
  REGISTRO.push({ momento: iso(t - 70e3), usuario: quien.email, accion: "ver_clip", objeto: a.id, detalle: "", ip: "88.27.114.6" });
}
REGISTRO.push({ momento: iso(AHORA - 3600e3), usuario: "sistema", accion: "clip_caducado", objeto: "", detalle: "Retención de 30 días", ip: "" });
REGISTRO.push({ momento: iso(AHORA - 120e3), usuario: YO.email, accion: "inicio_sesion", objeto: "", detalle: "", ip: "88.27.114.6" });
REGISTRO.sort((a, b) => b.momento.localeCompare(a.momento));

const publica = (a: Alerta & { _clip?: string }): Alerta => { const { _clip, ...r } = a; void _clip; return r; };

function estadisticas(): Estadisticas {
  const desde = AHORA - 14 * 86400e3;
  const xs = ALERTAS.filter((a) => new Date(a.inicio).getTime() >= desde);
  const cuenta = <K extends string>(f: (a: Alerta) => K) => xs.reduce<Record<string, number>>((m, a) => ((m[f(a)] = (m[f(a)] ?? 0) + 1), m), {});
  const rev = xs.filter((a) => a.estado === "descartada" || a.estado === "confirmada");
  const porCam = cuenta((a) => `${a.camara.nombre} · ${a.camara.tienda.split("· ")[1]}`);
  const porDia = cuenta((a) => a.inicio.slice(0, 10));
  return {
    total: xs.length, pendientes: xs.filter((a) => a.estado === "nueva").length,
    tasa_descartadas: rev.length ? rev.filter((a) => a.estado === "descartada").length / rev.length : null,
    por_estado: cuenta((a) => a.estado), por_prioridad: cuenta((a) => a.prioridad),
    por_camara: Object.entries(porCam).map(([camara, alertas]) => ({ camara, alertas })).sort((a, b) => b.alertas - a.alertas),
    por_dia: Array.from({ length: 14 }, (_, i) => { const d = iso(AHORA - (13 - i) * 86400e3).slice(0, 10); return { dia: d, alertas: porDia[d] ?? 0 }; }),
  };
}

export async function demoApi<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  await new Promise((r) => setTimeout(r, 120));
  const metodo = (opciones.method ?? "GET").toUpperCase();
  const [camino, query] = ruta.split("?");
  const q = new URLSearchParams(query);
  const r = <X,>(x: X) => x as unknown as T;
  if (camino === "/yo") return r(YO);
  if (camino === "/alertas") {
    const e = q.get("estado");
    return r(ALERTAS.filter((a) => !e || a.estado === e).map(publica));
  }
  const m = camino.match(/^\/alertas\/([^/]+)(\/enlace-clip)?$/);
  if (m) {
    const a = ALERTAS.find((x) => x.id === m[1]);
    if (!a) throw new Error("Alerta no encontrada");
    if (m[2]) {
      REGISTRO.unshift({ momento: iso(Date.now()), usuario: YO.email, accion: "ver_clip", objeto: a.id, detalle: "", ip: "88.27.114.6" });
      return r({ url: (window as unknown as { __CLIPS__?: Record<string, string> }).__CLIPS__?.[a._clip] ?? "" });
    }
    if (metodo === "PATCH") {
      const c = JSON.parse(String(opciones.body ?? "{}"));
      if (c.estado) { a.estado = c.estado; a.revisada_en = iso(Date.now()); }
      if (c.nota !== undefined) a.nota = c.nota;
      REGISTRO.unshift({ momento: iso(Date.now()), usuario: YO.email, accion: "cambiar_alerta", objeto: a.id, detalle: `estado=${a.estado}`, ip: "88.27.114.6" });
    }
    return r(publica(a));
  }
  if (camino === "/camaras") return r(CAMARAS);
  const mc = camino.match(/^\/camaras\/([^/]+)$/);
  if (mc && metodo === "PATCH") {
    const c = CAMARAS.find((x) => x.id === mc[1])!;
    Object.assign(c, JSON.parse(String(opciones.body ?? "{}")));
    return r(c);
  }
  if (camino === "/estadisticas") return r(estadisticas());
  if (camino === "/registro") return r(REGISTRO);
  if (camino === "/usuarios") {
    if (metodo === "POST") {
      const n = JSON.parse(String(opciones.body ?? "{}"));
      const u = { id: `u${USUARIOS.length + 1}`, nombre: n.nombre, email: n.email, rol: n.rol, activo: true };
      USUARIOS.push(u);
      return r(u);
    }
    return r(USUARIOS);
  }
  throw new Error("No disponible en la demo");
}

// Simula el WebSocket: una alerta nueva cada ~25 s
export function demoEscuchar(alRecibir: (m: { tipo: string; nueva?: boolean; alerta?: Alerta }) => void, alCambiarEstado: (c: boolean) => void) {
  setTimeout(() => alCambiarEstado(true), 300);
  const t = setInterval(() => {
    const a = crearAlerta(Date.now() - 12000, "nueva");
    ALERTAS.unshift(a);
    alRecibir({ tipo: "alerta", nueva: true, alerta: publica(a) });
  }, 25000);
  return () => clearInterval(t);
}
