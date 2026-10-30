"""Seguimiento de personas entre fotogramas (asigna un track_id estable).

MVP: emparejamiento voraz por IoU de cajas. Suficiente para pasillos con pocas personas.
Siguiente paso previsto: ByteTrack (licencia MIT) cuando haya vídeo real con cruces y oclusiones que lo justifiquen.
"""
from __future__ import annotations

from dataclasses import dataclass

from .tipos import Persona


def iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@dataclass
class _Pista:
    track_id: int
    caja: tuple
    sin_ver: int = 0


class Seguidor:
    def __init__(self, iou_min: float = 0.3, max_sin_ver: int = 15):
        self.iou_min, self.max_sin_ver = iou_min, max_sin_ver
        self.pistas: list[_Pista] = []
        self._siguiente = 1

    def actualizar(self, personas: list[Persona]) -> list[Persona]:
        pares = sorted(((iou(p.caja, d.caja), i, j) for i, p in enumerate(self.pistas) for j, d in enumerate(personas)),
                       reverse=True)
        usadas_p, usadas_d = set(), set()
        for valor, i, j in pares:
            if valor < self.iou_min:
                break
            if i in usadas_p or j in usadas_d:
                continue
            usadas_p.add(i)
            usadas_d.add(j)
            self.pistas[i].caja, self.pistas[i].sin_ver = personas[j].caja, 0
            personas[j].track_id = self.pistas[i].track_id
        for j, d in enumerate(personas):
            if j not in usadas_d:
                pista = _Pista(self._siguiente, d.caja)
                self._siguiente += 1
                self.pistas.append(pista)
                d.track_id = pista.track_id
        for i, pista in enumerate(self.pistas):
            if i not in usadas_p and pista.caja is not None and all(pista.track_id != d.track_id for d in personas):
                pista.sin_ver += 1
        self.pistas = [p for p in self.pistas if p.sin_ver <= self.max_sin_ver]
        return personas
