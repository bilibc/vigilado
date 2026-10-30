"""Escenarios sintéticos para probar la LÓGICA del analizador sin cámaras.

Genera esqueletos (17 puntos COCO) de una persona vista de frente que anda, coge de una estantería y hace distintos gestos.
Sirve para tests y demos del sistema completo. NO sirve para medir la precisión real: eso solo se mide con vídeo real
pasado por el modelo de pose (ver docs/pruebas.md).
"""
from __future__ import annotations

import math

import numpy as np

from .tipos import Fotograma, Persona
from .zonas import Zona

ANCHO, ALTO, FPS = 1280, 720, 10
H = 420.0            # altura de la persona en píxeles
SUELO = 660.0        # y de los pies
L_BRAZO, L_ANTEBRAZO = 0.17 * H, 0.16 * H

# Zonas de la cámara sintética (normalizadas)
ZONAS = [
    Zona("Estantería perfumes", "estanteria", [[0.04, 0.24], [0.22, 0.24], [0.22, 0.62], [0.04, 0.62]]),
    Zona("Caja", "caja", [[0.0, 0.86], [0.12, 0.86], [0.12, 1.0], [0.0, 1.0]]),
    Zona("Salida", "salida", [[0.86, 0.86], [1.0, 0.86], [1.0, 1.0], [0.86, 1.0]]),
]
ESTANTERIA_PUNTO = (240.0, 330.0)  # dónde «coge» la mano dentro de la estantería


def _ik(hombro, objetivo, lado):
    """Codo para que la muñeca llegue al objetivo (2 segmentos). lado: -1 izquierda de la imagen, +1 derecha."""
    s, w = np.asarray(hombro, float), np.asarray(objetivo, float)
    d = w - s
    dist = float(np.linalg.norm(d))
    maximo = L_BRAZO + L_ANTEBRAZO - 1e-3
    if dist > maximo:
        w = s + d / dist * maximo
        dist = maximo
    dist = max(dist, 1e-3)
    a = (L_BRAZO ** 2 - L_ANTEBRAZO ** 2 + dist ** 2) / (2 * dist)
    h = math.sqrt(max(L_BRAZO ** 2 - a ** 2, 0.0))
    base = s + a * (w - s) / dist
    perp = np.array([-(w - s)[1], (w - s)[0]]) / dist
    codo = base + perp * h * (1 if lado > 0 else -1)
    if (codo[0] - s[0]) * lado < 0:  # el codo hacia fuera del cuerpo
        codo = base - perp * h * (1 if lado > 0 else -1)
    return codo, w


def esqueleto(cx: float, objetivo_i, objetivo_d) -> np.ndarray:
    """17 puntos. objetivo_i/d: posición de la muñeca (None = brazo colgando)."""
    p = np.zeros((17, 2))
    hombro_y, cadera_y = SUELO - 0.82 * H, SUELO - 0.50 * H
    p[0] = (cx, SUELO - 0.94 * H)                          # nariz
    p[1], p[2] = (cx - 0.03 * H, p[0][1] - 0.02 * H), (cx + 0.03 * H, p[0][1] - 0.02 * H)
    p[3], p[4] = (cx - 0.06 * H, p[0][1]), (cx + 0.06 * H, p[0][1])
    p[5], p[6] = (cx - 0.11 * H, hombro_y), (cx + 0.11 * H, hombro_y)
    p[11], p[12] = (cx - 0.08 * H, cadera_y), (cx + 0.08 * H, cadera_y)
    p[13], p[14] = (cx - 0.08 * H, SUELO - 0.26 * H), (cx + 0.08 * H, SUELO - 0.26 * H)
    p[15], p[16] = (cx - 0.08 * H, SUELO), (cx + 0.08 * H, SUELO)
    for (i_h, i_c, i_m, lado, obj) in ((5, 7, 9, -1, objetivo_i), (6, 8, 10, 1, objetivo_d)):
        if obj is None:
            obj = (p[i_h][0] + lado * 0.02 * H, p[i_h][1] + 0.33 * H)
        p[i_c], p[i_m] = _ik(p[i_h], obj, lado)
    return p


# --- objetivos de muñeca típicos (en función de cx) ---
def bolsillo(cx, lado):   return (cx + lado * 0.05 * H, SUELO - 0.52 * H)
def cintura(cx, lado):    return (cx + lado * 0.02 * H, SUELO - 0.58 * H)    # bajo la ropa, parte baja del torso
def pecho_alto(cx, lado): return (cx + lado * 0.02 * H, SUELO - 0.76 * H)    # examinar producto o mirar el móvil
def mano_otra(cx, lado):  return (cx - lado * 0.08 * H, SUELO - 0.47 * H)    # junto a la otra mano (cesta)


def _secuencia(claves, cx0, ruido, semilla, track_id=1):
    """claves: lista de (duración s, cx_final, objetivo_i(cx), objetivo_d(cx)). Interpola y genera fotogramas."""
    rng = np.random.default_rng(semilla)
    frames, t, cx = [], 0.0, cx0
    prev = esqueleto(cx0, None, None)
    for dur, cx_fin, oi, od in claves:
        n = max(1, int(round(dur * FPS)))
        cx_ini = cx
        for k in range(1, n + 1):
            a = k / n
            cx = cx_ini + (cx_fin - cx_ini) * a
            fin = esqueleto(cx, oi(cx) if oi else None, od(cx) if od else None)
            base = esqueleto(cx, None, None)
            pts = prev_interp(prev, fin, base, a)
            if ruido:
                pts = pts + rng.normal(0, ruido, pts.shape)
            conf = np.full(17, 0.9)
            if ruido and rng.random() < 0.05:  # a veces se pierde una muñeca un instante
                conf[9 + int(rng.random() < 0.5)] = 0.1
            caja = (pts[:, 0].min() - 15, pts[:, 1].min() - 30, pts[:, 0].max() + 15, SUELO + 5)
            frames.append(Fotograma(t=round(t, 3), ancho=ANCHO, alto=ALTO,
                                    personas=[Persona(track_id, caja, pts, conf)]))
            t += 1 / FPS
        prev = esqueleto(cx, oi(cx) if oi else None, od(cx) if od else None)
    return frames


def prev_interp(prev, fin, base, a):
    """Mueve brazos de la pose previa a la final (el cuerpo ya está en su sitio)."""
    out = fin.copy()
    for i in (7, 8, 9, 10):
        desplaz = prev[i] - (prev[5] if i % 2 else prev[6])
        hombro = fin[5] if i % 2 else fin[6]
        out[i] = (hombro + desplaz) * (1 - a) + fin[i] * a
    return out


def _coge(lado=-1):
    return lambda cx: ESTANTERIA_PUNTO if lado == -1 else None


# Cada escenario: (descripción, ¿debería avisar?, claves)
def escenarios():
    I = -1
    andar = lambda d, x: (d, x, None, None)
    coge = (1.0, 380, lambda cx: ESTANTERIA_PUNTO, None)
    sujeta = (0.6, 380, lambda cx: ESTANTERIA_PUNTO, None)
    retira = (0.6, 380, None, None)
    return {
        "ocultacion_bolsillo_y_sale": ("Coge, mano al bolsillo 1,2 s y sale sin pasar por caja", True, [
            andar(2.0, 380), coge, sujeta, retira, (0.4, 380, lambda cx: bolsillo(cx, I), None),
            (1.2, 380, lambda cx: bolsillo(cx, I), None), retira, andar(4.0, 1200)]),
        "ocultacion_ropa_y_paga": ("Coge, mete la mano bajo la ropa y luego pasa por caja", True, [
            andar(2.0, 380), coge, sujeta, retira, (0.4, 380, lambda cx: cintura(cx, I), None),
            (1.0, 380, lambda cx: cintura(cx, I), None), retira, andar(2.5, 60), andar(1.5, 60), andar(5.0, 1200)]),
        "manipulacion_repetida": ("Coge tres veces y al final mano al bolsillo", True, [
            andar(2.0, 380), coge, retira, coge, retira, coge, retira, (0.4, 380, lambda cx: bolsillo(cx, I), None),
            (1.0, 380, lambda cx: bolsillo(cx, I), None), retira, andar(3.0, 700)]),
        "movil_sin_coger": ("Saca el móvil del bolsillo sin haber cogido nada", False, [
            andar(2.0, 380), (0.4, 380, lambda cx: bolsillo(cx, I), None), (1.5, 380, lambda cx: bolsillo(cx, I), None),
            (0.5, 380, lambda cx: pecho_alto(cx, I), None), (2.0, 380, lambda cx: pecho_alto(cx, I), None), retira, andar(3.0, 1200)]),
        "coge_y_mete_en_cesta": ("Coge y lo deja en la cesta que lleva en la otra mano", False, [
            andar(2.0, 380), coge, sujeta, retira, (0.5, 380, lambda cx: mano_otra(cx, I), None),
            (1.0, 380, lambda cx: mano_otra(cx, I), None), retira, andar(2.5, 60), andar(2.0, 60)]),
        "coge_examina_devuelve": ("Coge, lo mira a la altura del pecho y lo devuelve", False, [
            andar(2.0, 380), coge, sujeta, retira, (0.5, 380, lambda cx: pecho_alto(cx, I), None),
            (2.0, 380, lambda cx: pecho_alto(cx, I), None), coge, sujeta, retira, andar(3.0, 1200)]),
        "coge_y_va_a_caja_con_el_producto": ("Coge y va a caja con el producto en la mano", False, [
            andar(2.0, 380), coge, sujeta, retira, andar(2.5, 60), andar(2.0, 60), andar(5.0, 1200)]),
        "pasea_brazos_colgando": ("Pasa por delante de la estantería sin tocar nada", False, [
            andar(3.0, 380), andar(1.0, 380), andar(3.0, 1200)]),
    }


def generar(nombre: str, ruido: float = 0.0, semilla: int = 0):
    desc, avisa, claves = escenarios()[nombre]
    return desc, avisa, _secuencia(claves, 700.0, ruido, semilla)
