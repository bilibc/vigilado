"""Medición honesta de la precisión.

1) Sintético: comprueba la LÓGICA de las reglas con esqueletos generados (con ruido). No mide la IA real.
2) Vídeos reales etiquetados: el número que importa. CSV con columnas
       video,inicio_s,fin_s,tipo        (tipo = ocultacion | normal)
   Cada evento se cuenta como acierto si su gesto de ocultación cae dentro de [inicio-2 s, fin+2 s] de una etiqueta
   «ocultacion». Se calculan sensibilidad (ocultaciones detectadas), precisión (alertas que eran reales) y
   falsas alarmas por hora de vídeo.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from . import sintetico
from .analizador import Analizador, Parametros
from .seguimiento import Seguidor


def correr(fotogramas, zonas, parametros=None, seguir=False) -> list:
    a = Analizador("eval", zonas, parametros)
    seg = Seguidor() if seguir else None
    eventos = {}
    for f in fotogramas:
        if seg:
            seg.actualizar(f.personas)
        for e in a.actualizar(f):
            eventos[e.evento_id] = e
    return list(eventos.values())


def evaluar_sintetico(ruidos=(0.0, 3.0, 6.0), semillas=10, parametros=None) -> dict:
    filas, tot = [], defaultdict(int)
    for nombre, (desc, avisa, _) in sintetico.escenarios().items():
        for ruido in ruidos:
            aciertos = 0
            for s in range(semillas):
                _, _, frames = sintetico.generar(nombre, ruido=ruido, semilla=s)
                hay = bool(correr(frames, sintetico.ZONAS, parametros))
                aciertos += hay == avisa
                tot[("VP" if hay else "FN") if avisa else ("FP" if hay else "VN")] += 1
            filas.append({"escenario": nombre, "descripcion": desc, "debe_avisar": avisa, "ruido_px": ruido,
                          "aciertos": aciertos, "pruebas": semillas})
    return {"filas": filas, "totales": dict(tot), **_metricas(tot)}


def _metricas(t) -> dict:
    vp, fp, fn = t.get("VP", 0), t.get("FP", 0), t.get("FN", 0)
    return {"sensibilidad": round(vp / (vp + fn), 3) if vp + fn else None,
            "precision": round(vp / (vp + fp), 3) if vp + fp else None}


def evaluar_videos(etiquetas_csv: str, perceptor_factory, zonas, parametros=None, margen=2.0) -> dict:
    """perceptor_factory(video) -> iterable de Fotograma ya con track_id (o sin él: se aplica Seguidor)."""
    por_video = defaultdict(list)
    with open(etiquetas_csv, encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            por_video[fila["video"]].append((float(fila["inicio_s"]), float(fila["fin_s"]), fila["tipo"].strip()))
    tot, duracion, detalle = defaultdict(int), 0.0, []
    for video, etiquetas in por_video.items():
        fotogramas = list(perceptor_factory(video))
        if fotogramas:
            duracion += fotogramas[-1].t - fotogramas[0].t
        eventos = correr(fotogramas, zonas, parametros, seguir=True)
        ocultas = [(i, f) for i, f, tipo in etiquetas if tipo == "ocultacion"]
        detectadas = set()
        for ev in eventos:
            t_gesto = next((p.t for p in ev.pasos if p.tipo == "ocultacion"), ev.inicio)
            casa = next((k for k, (i, f) in enumerate(ocultas) if i - margen <= t_gesto <= f + margen), None)
            if casa is None:
                tot["FP"] += 1
            else:
                detectadas.add(casa)
            detalle.append({"video": video, "t": round(t_gesto, 2), "tipo": ev.tipo, "prioridad": ev.prioridad,
                            "correcto": casa is not None})
        tot["VP"] += len(detectadas)
        tot["FN"] += len(ocultas) - len(detectadas)
    horas = duracion / 3600 if duracion else 0
    return {"totales": dict(tot), **_metricas(tot), "horas_video": round(horas, 3),
            "falsas_alarmas_por_hora": round(tot["FP"] / horas, 2) if horas else None, "eventos": detalle}


def imprimir(informe: dict):
    for f in informe.get("filas", []):
        marca = "✔" if f["aciertos"] == f["pruebas"] else "✘"
        print(f"{marca} {f['escenario']:<34} ruido {f['ruido_px']:>4} px  {f['aciertos']}/{f['pruebas']}")
    print("Totales:", informe["totales"], "| sensibilidad:", informe["sensibilidad"], "| precisión:", informe["precision"])
    if informe.get("falsas_alarmas_por_hora") is not None:
        print("Falsas alarmas por hora:", informe["falsas_alarmas_por_hora"], "| horas de vídeo:", informe["horas_video"])


def guardar(informe: dict, ruta: str):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    Path(ruta).write_text(json.dumps(informe, ensure_ascii=False, indent=1))
