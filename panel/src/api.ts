// Cliente de la API de Vigilado.

export type Paso = { t: number; tipo: string; texto: string; datos?: Record<string, unknown> };
export type Alerta = {
  id: string; tipo: string; titulo: string; puntuacion: number; prioridad: "alta" | "media" | "baja";
  inicio: string; actualizada: string; pasos: Paso[]; estado: Estado; nota: string; simulacion: boolean;
  tiene_clip: boolean; clip_borrado: boolean; revisada_en: string | null;
  camara: { id: string; nombre: string; ubicacion: string; tienda: string; tienda_id: string };
};
export type Estado = "nueva" | "revisada" | "descartada" | "confirmada";
export type Camara = {
  id: string; codigo: string; nombre: string; ubicacion: string; activa: boolean; en_linea: boolean;
  fps: number; tienda_id: string; tienda: string; ultimo_latido: string | null;
};
export type Usuario = { id: string; nombre: string; email: string; rol: "propietario" | "encargado" | "lectura" };
export type Estadisticas = {
  total: number; pendientes: number; tasa_descartadas: number | null;
  por_estado: Record<string, number>; por_prioridad: Record<string, number>;
  por_camara: { camara: string; alertas: number }[]; por_dia: { dia: string; alertas: number }[];
};

const CLAVE = "vigilado.sesion";

export const sesion = {
  token: () => localStorage.getItem(CLAVE),
  guardar: (t: string) => localStorage.setItem(CLAVE, t),
  cerrar: () => { localStorage.removeItem(CLAVE); location.href = "/"; },
};

export async function api<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const r = await fetch(`/api/v1${ruta}`, {
    ...opciones,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${sesion.token() ?? ""}`, ...(opciones.headers || {}) },
  });
  if (r.status === 401 && ruta !== "/sesion") sesion.cerrar();
  if (!r.ok) {
    const cuerpo = await r.json().catch(() => ({}));
    throw new Error(typeof cuerpo.detail === "string" ? cuerpo.detail : `Error ${r.status}`);
  }
  return r.json();
}

// Enlace firmado de 5 minutos para un solo clip (la sesión nunca va en la URL)
export const enlaceClip = (id: string) => api<{ url: string }>(`/alertas/${id}/enlace-clip`).then((r) => r.url);

// WebSocket con reconexión automática
export function escuchar(alRecibir: (msg: { tipo: string; nueva?: boolean; alerta?: Alerta }) => void,
                         alCambiarEstado: (conectado: boolean) => void) {
  let ws: WebSocket | null = null;
  let cerrado = false;
  let espera = 1000;
  const abrir = () => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/api/v1/ws`);
    ws.onopen = () => { ws?.send(JSON.stringify({ token: sesion.token() })); espera = 1000; alCambiarEstado(true); };
    ws.onmessage = (e) => alRecibir(JSON.parse(e.data));
    ws.onclose = () => {
      alCambiarEstado(false);
      if (!cerrado) setTimeout(abrir, (espera = Math.min(espera * 2, 15000)));
    };
  };
  abrir();
  return () => { cerrado = true; ws?.close(); };
}

export const fecha = (iso: string) =>
  new Date(iso).toLocaleString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" });

export const haceCuanto = (iso: string) => {
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "ahora";
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  if (s < 86400) return `hace ${Math.round(s / 3600)} h`;
  return `hace ${Math.round(s / 86400)} d`;
};
