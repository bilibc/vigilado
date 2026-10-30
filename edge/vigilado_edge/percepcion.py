"""Percepción: de una imagen a personas con esqueleto.

- PerceptorRTM: modelo real. YOLOX (detección de personas) + RTMPose (pose de 17 puntos) vía `rtmlib`
  (Apache 2.0, se ejecuta con ONNX Runtime en CPU o GPU). Los pesos se descargan solos la primera vez desde
  download.openmmlab.com, así que el equipo necesita internet ese primer arranque.
- PerceptorReproduccion: lee poses guardadas en un .jsonl (volcadas antes con `vigilado-edge volcar-poses`).
  Permite ajustar reglas sin volver a pasar el vídeo por la GPU.

Sin reconocimiento facial ni identificación: solo puntos del esqueleto y cajas.
"""
from __future__ import annotations

import json

import numpy as np

from .tipos import Fotograma, Persona


class PerceptorRTM:
    def __init__(self, modo: str = "balanced", dispositivo: str = "cpu", conf_persona: float = 0.4):
        try:
            from rtmlib import Body  # import perezoso: solo hace falta en el equipo de la tienda
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Falta rtmlib: pip install -r requirements-modelo.txt") from e
        self.modelo = Body(mode=modo, backend="onnxruntime", device=dispositivo)
        self.conf_persona = conf_persona

    def __call__(self, imagen: np.ndarray, t: float) -> Fotograma:
        alto, ancho = imagen.shape[:2]
        cajas = self.modelo.det_model(imagen)
        personas = []
        if len(cajas):
            puntos, conf = self.modelo.pose_model(imagen, bboxes=cajas)
            for caja, p, c in zip(cajas, puntos, conf):
                personas.append(Persona(0, tuple(float(v) for v in caja[:4]), np.asarray(p, float)[:17],
                                        np.asarray(c, float)[:17]))
        return Fotograma(t=t, ancho=ancho, alto=alto, personas=personas)


def fotograma_a_dict(f: Fotograma) -> dict:
    return {"t": f.t, "ancho": f.ancho, "alto": f.alto,
            "personas": [{"id": p.track_id, "caja": [round(v, 1) for v in p.caja],
                          "puntos": np.round(p.puntos, 1).tolist(), "conf": np.round(p.confianzas, 3).tolist()}
                         for p in f.personas]}


def dict_a_fotograma(d: dict) -> Fotograma:
    return Fotograma(t=d["t"], ancho=d["ancho"], alto=d["alto"],
                     personas=[Persona(p["id"], tuple(p["caja"]), np.asarray(p["puntos"], float), np.asarray(p["conf"], float))
                               for p in d["personas"]])


class PerceptorReproduccion:
    """Devuelve las poses guardadas, en orden, ignorando la imagen."""

    def __init__(self, ruta: str):
        with open(ruta, encoding="utf-8") as fh:
            self.fotogramas = [dict_a_fotograma(json.loads(linea)) for linea in fh if linea.strip()]
        self._i = 0

    def __call__(self, imagen, t: float) -> Fotograma:
        if self._i >= len(self.fotogramas):
            return Fotograma(t=t, ancho=0, alto=0)
        f = self.fotogramas[self._i]
        self._i += 1
        return f
