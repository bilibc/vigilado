"""Zonas que marca el comercio en cada cámara (estanterías, caja, salida).

Los polígonos se guardan en coordenadas normalizadas (0..1) para que no dependan de la resolución.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TIPOS_ZONA = ("estanteria", "caja", "salida")


@dataclass
class Zona:
    nombre: str
    tipo: str
    poligono: np.ndarray  # (N, 2) normalizado

    def __post_init__(self):
        if self.tipo not in TIPOS_ZONA:
            raise ValueError(f"Tipo de zona desconocido: {self.tipo} (válidos: {', '.join(TIPOS_ZONA)})")
        self.poligono = np.asarray(self.poligono, dtype=float)
        if self.poligono.ndim != 2 or len(self.poligono) < 3:
            raise ValueError(f"La zona «{self.nombre}» necesita al menos 3 puntos")

    def contiene(self, x: float, y: float, ancho: int, alto: int) -> bool:
        return punto_en_poligono(x / ancho, y / alto, self.poligono)


def punto_en_poligono(x: float, y: float, poligono: np.ndarray) -> bool:
    """Algoritmo del rayo. Puntos sobre el borde cuentan como dentro de forma aproximada."""
    dentro = False
    n = len(poligono)
    j = n - 1
    for i in range(n):
        xi, yi = poligono[i]
        xj, yj = poligono[j]
        if (yi > y) != (yj > y):
            x_corte = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_corte:
                dentro = not dentro
        j = i
    return dentro


def zonas_desde_config(lista: list[dict]) -> list[Zona]:
    return [Zona(nombre=z["nombre"], tipo=z["tipo"], poligono=z["poligono"]) for z in lista or []]
