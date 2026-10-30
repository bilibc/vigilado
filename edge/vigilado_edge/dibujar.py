"""Dibujo de zonas, esqueletos y avisos (vídeo de depuración y clips de alerta)."""
from __future__ import annotations

import cv2
import numpy as np

from .tipos import Fotograma

COLOR_ZONA = {"estanteria": (60, 170, 255), "caja": (90, 200, 90), "salida": (80, 80, 230)}
HUESOS = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (0, 5), (0, 6)]


def zonas(img, lista):
    capa = img.copy()
    h, w = img.shape[:2]
    for z in lista:
        pts = (z.poligono * [w, h]).astype(np.int32)
        cv2.fillPoly(capa, [pts], COLOR_ZONA[z.tipo])
        cv2.putText(img, z.nombre, tuple(pts[0] + [6, 22]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.addWeighted(capa, 0.18, img, 0.82, 0, img)
    return img


def esqueletos(img, f: Fotograma, destacar: int | None = None, color_normal=(240, 240, 240)):
    for p in f.personas:
        color = (60, 60, 255) if p.track_id == destacar else color_normal
        for a, b in HUESOS:
            if p.confianzas[a] > 0.3 and p.confianzas[b] > 0.3:
                cv2.line(img, tuple(p.puntos[a].astype(int)), tuple(p.puntos[b].astype(int)), color, 3, cv2.LINE_AA)
        for i in (9, 10):
            if p.confianzas[i] > 0.3:
                cv2.circle(img, tuple(p.puntos[i].astype(int)), 7, (0, 220, 255), -1, cv2.LINE_AA)
        x1, y1, x2, y2 = (int(v) for v in p.caja)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, f"#{p.track_id}", (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
    return img


def destacar_caja(img, f: Fotograma, track_id: int):
    for p in f.personas:
        if p.track_id == track_id:
            x1, y1, x2, y2 = (int(v) for v in p.caja)
            cv2.rectangle(img, (x1, y1), (x2, y2), (60, 60, 255), 3)
    return img


def difuminar_cabezas(img, f: Fotograma):
    """Difumina la zona de la cabeza (puntos 0-4) de todas las personas. Opcional por privacidad."""
    for p in f.personas:
        cab = p.puntos[:5][p.confianzas[:5] > 0.3]
        if len(cab) == 0:
            continue
        cx, cy = cab.mean(axis=0)
        r = int(max(20, (p.caja[2] - p.caja[0]) * 0.35))
        x1, y1 = max(0, int(cx - r)), max(0, int(cy - r * 1.2))
        x2, y2 = min(img.shape[1], int(cx + r)), min(img.shape[0], int(cy + r))
        if x2 > x1 and y2 > y1:
            img[y1:y2, x1:x2] = cv2.GaussianBlur(img[y1:y2, x1:x2], (0, 0), 15)
    return img


def rotulo(img, texto, color=(40, 40, 230)):
    cv2.rectangle(img, (0, 0), (img.shape[1], 44), color, -1)
    cv2.putText(img, texto, (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def lienzo_sintetico(ancho, alto):
    """Fondo de «tienda» para los vídeos de demo sintéticos."""
    img = np.full((alto, ancho, 3), (236, 240, 244), np.uint8)
    cv2.rectangle(img, (0, int(alto * 0.86)), (ancho, alto), (205, 212, 220), -1)
    cv2.putText(img, "SIMULACION - esqueletos sinteticos, no es video real", (16, alto - 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (90, 90, 90), 1, cv2.LINE_AA)
    return img
