"""Tipos de datos compartidos por todo el motor."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Índices de los 17 puntos del esqueleto en formato COCO (los que devuelve RTMPose).
NARIZ = 0
HOMBRO_I, HOMBRO_D = 5, 6
CODO_I, CODO_D = 7, 8
MUNECA_I, MUNECA_D = 9, 10
CADERA_I, CADERA_D = 11, 12
RODILLA_I, RODILLA_D = 13, 14

# Para cada mano: (muñeca, codo, hombro, cadera del mismo lado, cadera del otro lado)
BRAZOS = {
    "izquierda": (MUNECA_I, CODO_I, HOMBRO_I, CADERA_I, CADERA_D),
    "derecha": (MUNECA_D, CODO_D, HOMBRO_D, CADERA_D, CADERA_I),
}


@dataclass
class Persona:
    """Una persona en un fotograma. Coordenadas en píxeles de la imagen."""

    track_id: int
    caja: tuple[float, float, float, float]  # x1, y1, x2, y2
    puntos: np.ndarray  # (17, 2)
    confianzas: np.ndarray  # (17,)
    confianza_caja: float = 1.0

    def punto(self, i: int, minimo: float = 0.3):
        """Devuelve el punto i si su confianza es suficiente; si no, None."""
        if self.confianzas[i] < minimo:
            return None
        return self.puntos[i]


@dataclass
class Fotograma:
    """Resultado de la percepción de un fotograma."""

    t: float  # segundos (vídeo: desde el inicio; cámara: reloj de pared)
    ancho: int
    alto: int
    personas: list[Persona] = field(default_factory=list)


@dataclass
class Paso:
    """Un paso de la secuencia que explica una alerta."""

    t: float
    tipo: str  # coge | ocultacion | salida_sin_caja | paso_por_caja | manipulacion_repetida
    texto: str
    datos: dict = field(default_factory=dict)


@dataclass
class Evento:
    """Evento que merece revisión humana. Nunca es una acusación."""

    evento_id: str
    camara_id: str
    track_id: int
    tipo: str  # p. ej. «ocultacion_bolsillo»
    puntuacion: float
    prioridad: str  # baja | media | alta
    inicio: float
    actualizado: float
    pasos: list[Paso] = field(default_factory=list)
    caja: tuple[float, float, float, float] | None = None

    @property
    def titulo(self) -> str:
        return TITULOS.get(self.tipo, "Gesto compatible con ocultación")


TITULOS = {
    "ocultacion_bolsillo": "Gesto compatible con ocultación en bolsillo o cintura",
    "ocultacion_ropa": "Gesto compatible con ocultación bajo la ropa",
    "ocultacion_bolsa": "Gesto compatible con ocultación en bolsa o mochila",
}
