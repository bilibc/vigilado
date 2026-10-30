"""Tests de la lógica del analizador con escenarios sintéticos (sin modelo, sin cámara)."""
import numpy as np
import pytest

from vigilado_edge import sintetico
from vigilado_edge.analizador import Analizador, angulo, prioridad
from vigilado_edge.evaluar import correr, evaluar_sintetico
from vigilado_edge.seguimiento import Seguidor
from vigilado_edge.tipos import Persona
from vigilado_edge.zonas import Zona, punto_en_poligono

AVISAN = [n for n, (_, avisa, _) in sintetico.escenarios().items() if avisa]
CALLAN = [n for n, (_, avisa, _) in sintetico.escenarios().items() if not avisa]


@pytest.mark.parametrize("nombre", AVISAN)
def test_avisa_en_ocultaciones(nombre):
    _, _, frames = sintetico.generar(nombre, ruido=3, semilla=2)
    assert correr(frames, sintetico.ZONAS), f"{nombre} debería generar alerta"


@pytest.mark.parametrize("nombre", CALLAN)
def test_no_avisa_en_situaciones_legitimas(nombre):
    for semilla in range(5):
        _, _, frames = sintetico.generar(nombre, ruido=3, semilla=semilla)
        assert not correr(frames, sintetico.ZONAS), f"{nombre} no debería generar alerta (semilla {semilla})"


def test_salida_sin_caja_sube_a_prioridad_alta():
    _, _, frames = sintetico.generar("ocultacion_bolsillo_y_sale")
    (ev,) = correr(frames, sintetico.ZONAS)
    assert [p.tipo for p in ev.pasos] == ["coge", "ocultacion", "salida_sin_caja"]
    assert ev.prioridad == "alta"


def test_pasar_por_caja_baja_la_prioridad():
    _, _, frames = sintetico.generar("ocultacion_ropa_y_paga")
    (ev,) = correr(frames, sintetico.ZONAS)
    assert ev.tipo == "ocultacion_ropa"
    assert "paso_por_caja" in [p.tipo for p in ev.pasos]
    assert ev.prioridad == "baja"


def test_explicacion_legible():
    _, _, frames = sintetico.generar("manipulacion_repetida")
    (ev,) = correr(frames, sintetico.ZONAS)
    textos = " | ".join(p.texto for p in ev.pasos)
    assert "Coge en «Estantería perfumes»" in textos and "bolsillo" in textos and "productos cogidos" in textos


def test_un_evento_por_persona_y_no_duplicado():
    _, _, frames = sintetico.generar("ocultacion_bolsillo_y_sale")
    a = Analizador("c", sintetico.ZONAS)
    ids = {e.evento_id for f in frames for e in a.actualizar(f)}
    assert len(ids) == 1


def test_evaluacion_sintetica_sin_falsas_alarmas():
    inf = evaluar_sintetico(ruidos=(0.0, 3.0), semillas=4)
    assert inf["totales"].get("FP", 0) == 0
    assert inf["sensibilidad"] >= 0.95


def test_utilidades():
    assert round(angulo((0, 0), (1, 0), (2, 0))) == 180
    assert round(angulo((0, 1), (0, 0), (1, 0))) == 90
    assert prioridad(0.85) == "alta" and prioridad(0.65) == "media" and prioridad(0.5) == "baja"
    cuadrado = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
    assert punto_en_poligono(0.5, 0.5, cuadrado) and not punto_en_poligono(1.5, 0.5, cuadrado)
    with pytest.raises(ValueError):
        Zona("x", "almacen", cuadrado)


def test_seguidor_mantiene_identidad():
    s = Seguidor()
    p = lambda x: Persona(0, (x, 0, x + 100, 300), np.zeros((17, 2)), np.ones(17))
    a = s.actualizar([p(0), p(500)])
    b = s.actualizar([p(510), p(10)])
    assert {x.track_id for x in a} == {1, 2}
    assert b[0].track_id == a[1].track_id and b[1].track_id == a[0].track_id
