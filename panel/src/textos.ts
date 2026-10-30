// Textos en lenguaje llano para el panel (lo técnico se queda en la API).
import type { Alerta, Paso } from "./api";

export function titulo(a: Pick<Alerta, "tipo">): string {
  if (a.tipo.endsWith("ropa")) return "Posible ocultación bajo la ropa";
  if (a.tipo.endsWith("bolsa")) return "Posible ocultación en bolso o mochila";
  return "Posible ocultación en bolsillo";
}

export function paso(p: Paso): string {
  const zona = p.texto.match(/«(.+?)»/)?.[1];
  const region = String(p.datos?.region ?? (p.texto.includes("ropa") ? "ropa" : p.texto.includes("bolsa") ? "bolsa" : "bolsillo"));
  switch (p.tipo) {
    case "coge": return zona ? `Coge un producto de ${zona}` : "Coge un producto";
    case "ocultacion": return region === "ropa" ? "Mete la mano bajo la ropa" : region === "bolsa" ? "Mete la mano en un bolso o mochila" : "Se lleva la mano al bolsillo";
    case "salida_sin_caja": return "Va hacia la salida sin pasar por caja";
    case "paso_por_caja": return "Pasa por caja";
    case "manipulacion_repetida": return "Ha cogido varios productos seguidos";
    default: return p.texto;
  }
}

export const hora = (iso: string, mas = 0) =>
  new Date(new Date(iso).getTime() + mas * 1000).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export const dia = (iso: string) => {
  const d = new Date(iso);
  const hoy = new Date();
  const ayer = new Date(Date.now() - 86400e3);
  const hhmm = d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
  if (d.toDateString() === hoy.toDateString()) return `Hoy, ${hhmm}`;
  if (d.toDateString() === ayer.toDateString()) return `Ayer, ${hhmm}`;
  return `${d.toLocaleDateString("es-ES", { day: "numeric", month: "short" })}, ${hhmm}`;
};
