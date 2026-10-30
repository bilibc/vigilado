"""Tests de la tubería completa: vídeo real (sin modelo) → clips, reproducción de poses y evaluación con etiquetas."""
import csv
import json
from pathlib import Path

import cv2
import numpy as np

from vigilado_edge import evaluar, sintetico
from vigilado_edge.clips import Grabador
from vigilado_edge.fuente import Fuente, oculta_clave
from vigilado_edge.percepcion import PerceptorReproduccion, fotograma_a_dict
from vigilado_edge.publicador import Publicador, evento_a_dict

MUESTRA = Path(__file__).resolve().parents[2] / "muestras" / "vtest.avi"


def test_fuente_lee_video_a_la_frecuencia_pedida():
    if not MUESTRA.exists():
        return
    ts = [t for t, _ in Fuente(str(MUESTRA), fps_analisis=5)]
    assert len(ts) > 100
    assert abs((ts[1] - ts[0]) - 0.2) < 0.06


def test_oculta_clave():
    assert oculta_clave("rtsp://admin:secreta@10.0.0.2:554/x") == "rtsp://admin:***@10.0.0.2:554/x"


def test_grabador_crea_clip_reproducible(tmp_path):
    g = Grabador(tmp_path, antes=1.0, despues=0.5, fps=10)
    _, _, frames = sintetico.generar("ocultacion_bolsillo_y_sale")
    clip = None
    for i, f in enumerate(frames[:60]):
        img = np.full((sintetico.ALTO, sintetico.ANCHO, 3), 200, np.uint8)
        if i == 30:
            g.pedir("ev1", 1, f.t)
        for _, ruta in g.anadir(f.t, img, f):
            clip = ruta
    assert clip and clip.exists() and clip.stat().st_size > 1000
    cap = cv2.VideoCapture(str(clip))
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) >= 14  # ~1 s antes + 0,5 s después a 10 fps


def test_reproduccion_de_poses_da_el_mismo_resultado(tmp_path):
    _, _, frames = sintetico.generar("ocultacion_bolsillo_y_sale", ruido=2, semilla=3)
    ruta = tmp_path / "poses.jsonl"
    ruta.write_text("\n".join(json.dumps(fotograma_a_dict(f)) for f in frames))
    rep = PerceptorReproduccion(str(ruta))
    assert len(evaluar.correr(rep.fotogramas, sintetico.ZONAS)) == len(evaluar.correr(frames, sintetico.ZONAS)) == 1


def test_evaluacion_con_etiquetas(tmp_path):
    poses = tmp_path / "poses"
    poses.mkdir()
    filas = []
    for nombre, (_, avisa, _) in sintetico.escenarios().items():
        _, _, frames = sintetico.generar(nombre, ruido=2, semilla=1)
        (poses / f"{nombre}.jsonl").write_text("\n".join(json.dumps(fotograma_a_dict(f)) for f in frames))
        filas.append({"video": f"{nombre}.mp4", "inicio_s": 3.0 if avisa else 0, "fin_s": 8.0 if avisa else 0,
                      "tipo": "ocultacion" if avisa else "normal"})
    etiquetas = tmp_path / "etiquetas.csv"
    with open(etiquetas, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["video", "inicio_s", "fin_s", "tipo"])
        w.writeheader()
        w.writerows(filas)
    fab = lambda v: PerceptorReproduccion(str(poses / (Path(v).stem + ".jsonl"))).fotogramas
    inf = evaluar.evaluar_videos(str(etiquetas), fab, sintetico.ZONAS)
    assert inf["totales"].get("VP") == 3 and inf["totales"].get("FN") == 0 and inf["totales"].get("FP", 0) == 0
    assert inf["falsas_alarmas_por_hora"] == 0


def test_publicador_sin_red_encola(tmp_path):
    pub = Publicador("http://127.0.0.1:9", "x", str(tmp_path / "cola"))
    _, _, frames = sintetico.generar("ocultacion_bolsillo_y_sale")
    (ev,) = evaluar.correr(frames, sintetico.ZONAS)
    assert pub.publicar(evento_a_dict(ev, reloj_real=False)) is False
    assert len(list((tmp_path / "cola").glob("*.json"))) == 1
