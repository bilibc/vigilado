"""Analizador de secuencias: convierte poses en el tiempo en eventos que merecen revisión humana.

Capa 1 del producto (reglas explicables). La idea:

    1. COGE      — una muñeca entra en una zona de estantería y vuelve a salir.
    2. OCULTA    — poco después, esa mano (o la otra) se queda un tiempo en una zona de ocultación del propio cuerpo:
                   bolsillo/cintura, bajo la ropa (torso con el codo muy doblado) o una bolsa detectada.
    3. CONTEXTO  — si luego pasa por caja, baja la prioridad; si sale de la tienda sin pasar por caja, sube.

Situaciones legítimas que se descartan a propósito:
    - Llevarse la mano al bolsillo sin haber cogido nada (móvil, cartera, llaves).
    - Brazos colgando al andar (codo estirado): no cuenta como bolsillo.
    - Dejar el producto a la vista (cesta, carro): anula el «coge».
    - Devolver el producto a la estantería: el «coge» se renueva, no se acumula.

Todo umbral está en `Parametros` para poder ajustarlo midiendo, no a ojo.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

import numpy as np

from .tipos import BRAZOS, CADERA_D, CADERA_I, HOMBRO_D, HOMBRO_I, Evento, Fotograma, Paso, Persona
from .zonas import Zona, punto_en_poligono


@dataclass
class Parametros:
    conf_punto: float = 0.3            # confianza mínima de un punto del esqueleto
    ventana_tras_coger: float = 6.0    # s: tiempo máximo entre coger y ocultar
    permanencia_min: float = 0.5       # s: tiempo mínimo con la mano en la zona de ocultación
    hueco_max: float = 0.3             # s: hueco tolerado (pérdida de un punto) sin romper la permanencia
    radio_bolsillo: float = 0.35       # × longitud del torso: distancia muñeca-cadera para «bolsillo»
    codo_bolsillo_max: float = 155.0   # grados: con el codo más estirado que esto, es un brazo colgando
    codo_ropa_max: float = 120.0       # grados: para «bajo la ropa» el codo tiene que ir muy doblado
    deposito_bajo: float = 0.5         # × torso por debajo de las caderas: mano baja = cesta/carro a la vista
    umbral_alerta: float = 0.5         # puntuación mínima para avisar
    repeticiones_manipulacion: int = 3  # «coge» en la ventana para considerarlo manipulación repetida
    ventana_manipulacion: float = 60.0
    reemision_min: float = 30.0        # s: no abrir otro evento de la misma persona antes de esto
    olvido: float = 10.0               # s sin ver a una persona para olvidar su estado


PUNTUACION_BASE = {"bolsillo": 0.55, "ropa": 0.6, "bolsa": 0.6}
TIPO_EVENTO = {"bolsillo": "ocultacion_bolsillo", "ropa": "ocultacion_ropa", "bolsa": "ocultacion_bolsa"}
TEXTO_REGION = {"bolsillo": "bolsillo o cintura", "ropa": "bajo la ropa (torso)", "bolsa": "bolsa o mochila"}


def prioridad(p: float) -> str:
    return "alta" if p >= 0.8 else "media" if p >= 0.6 else "baja"


def angulo(a, b, c) -> float:
    """Ángulo en b (grados) formado por a-b-c."""
    v1, v2 = np.asarray(a) - np.asarray(b), np.asarray(c) - np.asarray(b)
    n = np.linalg.norm(v1) * np.linalg.norm(v2)
    if n == 0:
        return 180.0
    return math.degrees(math.acos(float(np.clip(np.dot(v1, v2) / n, -1, 1))))


@dataclass
class _Mano:
    en_estanteria: bool = False
    zona_estanteria: str = ""
    ultimo_coge: float | None = None
    region: str | None = None
    region_desde: float = 0.0
    region_visto: float = 0.0
    region_registrada: bool = False


@dataclass
class _Estado:
    manos: dict = field(default_factory=lambda: {"izquierda": _Mano(), "derecha": _Mano()})
    coges: list = field(default_factory=list)
    visto: float = 0.0
    evento: Evento | None = None
    paso_caja: bool = False
    salio: bool = False
    previos: list = field(default_factory=list)  # últimos pasos sueltos (p. ej. «coge») antes de un evento


class Analizador:
    def __init__(self, camara_id: str, zonas: list[Zona], parametros: Parametros | None = None):
        self.camara_id = camara_id
        self.zonas = zonas
        self.p = parametros or Parametros()
        self.estados: dict[int, _Estado] = {}

    # ---------- geometría del cuerpo ----------
    def _region(self, persona: Persona, mano: str, objetos: list[dict]) -> tuple[str | None, dict]:
        mu, co, ho, cad_mismo, cad_otro = BRAZOS[mano]
        c = self.p.conf_punto
        w, e, s = persona.punto(mu, c), persona.punto(co, c), persona.punto(ho, c)
        hi, hd = persona.punto(CADERA_I, c), persona.punto(CADERA_D, c)
        si, sd = persona.punto(HOMBRO_I, c), persona.punto(HOMBRO_D, c)
        if w is None or hi is None or hd is None or si is None or sd is None:
            return None, {}
        cadera = (hi + hd) / 2
        torso = float(np.linalg.norm((si + sd) / 2 - cadera))
        if torso < 5:
            return None, {}
        codo = angulo(s, e, w) if (e is not None and s is not None) else 180.0
        datos = {"codo": round(codo, 1)}

        # Mano baja y abierta hacia el carro o la cesta: producto a la vista
        if w[1] > cadera[1] + self.p.deposito_bajo * torso:
            return "deposito", datos
        # Cesta en la otra mano: la muñeca va junto a la otra, que cuelga estirada por debajo de la cadera
        otro = "derecha" if mano == "izquierda" else "izquierda"
        mu2, co2, ho2 = BRAZOS[otro][:3]
        w2, e2, s2 = persona.punto(mu2, c), persona.punto(co2, c), persona.punto(ho2, c)
        if (w2 is not None and e2 is not None and s2 is not None and np.linalg.norm(w - w2) <= 0.3 * torso
                and angulo(s2, e2, w2) >= self.p.codo_bolsillo_max and w2[1] >= cadera[1] - 0.05 * torso):
            return "deposito", datos
        # Bolsa o mochila detectada por el modelo (si el perceptor la da)
        for ob in objetos:
            if ob.get("clase") in ("mochila", "bolso", "bolsa"):
                x1, y1, x2, y2 = ob["caja"]
                m = 0.15 * torso
                if x1 - m <= w[0] <= x2 + m and y1 - m <= w[1] <= y2 + m:
                    return "bolsa", datos
        # Bajo la ropa: muñeca en la mitad BAJA del torso (cintura) con el codo muy doblado.
        # La mitad alta se excluye: ahí se examina un producto o se mira el móvil.
        mi, md = (si + hi) / 2, (sd + hd) / 2
        poli = np.array([mi, md, hd, hi], dtype=float)
        centro = poli.mean(axis=0)
        poli = centro + (poli - centro) * 0.9
        if punto_en_poligono(w[0], w[1], poli) and codo <= self.p.codo_ropa_max:
            return "ropa", datos
        # Bolsillo o cintura: muñeca junto a una cadera con el codo doblado (no brazo colgando)
        if min(np.linalg.norm(w - hi), np.linalg.norm(w - hd)) <= self.p.radio_bolsillo * torso and codo <= self.p.codo_bolsillo_max:
            return "bolsillo", datos
        return None, datos

    def _zona_de(self, x: float, y: float, ancho: int, alto: int, tipo: str) -> Zona | None:
        for z in self.zonas:
            if z.tipo == tipo and z.contiene(x, y, ancho, alto):
                return z
        return None

    # ---------- bucle principal ----------
    def actualizar(self, f: Fotograma, objetos: list[dict] | None = None) -> list[Evento]:
        """Procesa un fotograma. Devuelve los eventos nuevos o actualizados en este fotograma."""
        objetos = objetos or []
        cambios: dict[str, Evento] = {}
        for persona in f.personas:
            st = self.estados.setdefault(persona.track_id, _Estado())
            st.visto = f.t
            self._manos(persona, st, f, objetos, cambios)
            self._contexto(persona, st, f, cambios)
        for tid in [t for t, s in self.estados.items() if f.t - s.visto > self.p.olvido]:
            del self.estados[tid]
        return list(cambios.values())

    def _manos(self, persona: Persona, st: _Estado, f: Fotograma, objetos, cambios):
        p = self.p
        for nombre, mano in st.manos.items():
            mu = BRAZOS[nombre][0]
            w = persona.punto(mu, p.conf_punto)
            # 1) COGE: la muñeca entra en una estantería y sale de ella
            if w is not None:
                z = self._zona_de(w[0], w[1], f.ancho, f.alto, "estanteria")
                if z is not None:
                    mano.en_estanteria, mano.zona_estanteria = True, z.nombre
                elif mano.en_estanteria:
                    mano.en_estanteria = False
                    mano.ultimo_coge = f.t
                    st.coges = [t for t in st.coges if f.t - t <= p.ventana_manipulacion] + [f.t]
                    st.previos = (st.previos + [Paso(f.t, "coge", f"Coge en «{mano.zona_estanteria}» (mano {nombre})")])[-10:]
            # 2) OCULTA
            region, datos = self._region(persona, nombre, objetos)
            if region == "deposito":
                # producto a la vista: anula el «coge» de las dos manos
                for m in st.manos.values():
                    m.ultimo_coge = None
                mano.region = None
                continue
            if region is None:
                if mano.region is not None and f.t - mano.region_visto > p.hueco_max:
                    mano.region, mano.region_registrada = None, False
                continue
            if region != mano.region:
                mano.region, mano.region_desde, mano.region_registrada = region, f.t, False
            mano.region_visto = f.t
            permanencia = f.t - mano.region_desde
            coge = max([m.ultimo_coge for m in st.manos.values() if m.ultimo_coge is not None], default=None)
            if (not mano.region_registrada and permanencia >= p.permanencia_min and coge is not None
                    and mano.region_desde - coge <= p.ventana_tras_coger and mano.region_desde >= coge):
                mano.region_registrada = True
                self._ocultacion(persona, st, f.t, region, nombre, permanencia, datos, cambios)

    def _ocultacion(self, persona, st: _Estado, t, region, mano, permanencia, datos, cambios):
        p = self.p
        punt = PUNTUACION_BASE[region] + min(0.15, max(0.0, (permanencia - p.permanencia_min) * 0.1))
        repetida = len(st.coges) >= p.repeticiones_manipulacion
        paso = Paso(t, "ocultacion", f"Mano {mano} a {TEXTO_REGION[region]} durante {permanencia:.1f} s",
                    {"region": region, "mano": mano, **datos})
        ev = st.evento
        if ev is None or t - ev.actualizado > p.reemision_min:
            ev = Evento(evento_id=uuid.uuid4().hex, camara_id=self.camara_id, track_id=persona.track_id,
                        tipo=TIPO_EVENTO[region], puntuacion=0.0, prioridad="baja", inicio=t, actualizado=t, caja=persona.caja)
            # el evento empieza con el «coge» que lo explica
            ultimo_coge = [x for x in st.previos if x.tipo == "coge"]
            ev.pasos.extend(ultimo_coge[-1:])
            if ultimo_coge:
                ev.inicio = ultimo_coge[-1].t
            st.evento, st.paso_caja, st.salio = ev, False, False
        ev.pasos.append(paso)
        if repetida and not any(x.tipo == "manipulacion_repetida" for x in ev.pasos):
            ev.pasos.append(Paso(t, "manipulacion_repetida", f"{len(st.coges)} productos cogidos en el último minuto"))
            punt += 0.1
        ev.puntuacion = round(min(1.0, max(ev.puntuacion, punt)), 2)
        ev.actualizado, ev.caja = t, persona.caja
        ev.prioridad = prioridad(ev.puntuacion)
        if ev.puntuacion >= p.umbral_alerta:
            cambios[ev.evento_id] = ev

    def _contexto(self, persona: Persona, st: _Estado, f: Fotograma, cambios):
        ev = st.evento
        if ev is None:
            return
        x1, _, x2, y2 = persona.caja
        pies = ((x1 + x2) / 2, y2)
        if not st.paso_caja and self._zona_de(*pies, f.ancho, f.alto, "caja"):
            st.paso_caja = True
            ev.pasos.append(Paso(f.t, "paso_por_caja", "Pasa por la zona de caja"))
            ev.puntuacion = round(max(0.3, ev.puntuacion - 0.25), 2)
        elif not st.salio and not st.paso_caja and self._zona_de(*pies, f.ancho, f.alto, "salida"):
            st.salio = True
            ev.pasos.append(Paso(f.t, "salida_sin_caja", "Se dirige a la salida sin pasar por caja"))
            ev.puntuacion = round(min(1.0, ev.puntuacion + 0.25), 2)
        else:
            return
        ev.prioridad, ev.actualizado = prioridad(ev.puntuacion), f.t
        if ev.puntuacion >= self.p.umbral_alerta or ev.evento_id in cambios:
            cambios[ev.evento_id] = ev
        elif any(x.tipo == "ocultacion" for x in ev.pasos):
            cambios[ev.evento_id] = ev  # ya se avisó: se manda la actualización aunque baje
