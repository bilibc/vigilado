"""Línea de órdenes del equipo de la tienda.

    vigilado-edge ejecutar --config config.yaml [--video-depuracion salida.mp4]
    vigilado-edge demo [--escenario NOMBRE|todos] [--api URL --token TOKEN]
    vigilado-edge volcar-poses --video tienda.mp4 --salida poses.jsonl
    vigilado-edge evaluar sintetico
    vigilado-edge evaluar videos --etiquetas etiquetas.csv --config config.yaml [--poses carpeta]
    vigilado-edge captura --fuente URL --salida captura.jpg      (imagen para dibujar las zonas)
"""
from __future__ import annotations

import argparse
import json
import logging
import threading
import time
from pathlib import Path

import cv2
import yaml

from . import dibujar, evaluar, sintetico
from .analizador import Analizador, Parametros
from .clips import Grabador
from .fuente import Fuente, oculta_clave
from .percepcion import PerceptorReproduccion, PerceptorRTM, fotograma_a_dict
from .publicador import Publicador, evento_a_dict
from .seguimiento import Seguidor
from .zonas import zonas_desde_config

log = logging.getLogger("vigilado")


def cargar_config(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def crear_perceptor(cfg: dict):
    m = cfg.get("modelo", {})
    if m.get("tipo", "rtm") == "reproduccion":
        return PerceptorReproduccion(m["poses"])
    return PerceptorRTM(modo=m.get("modo", "balanced"), dispositivo=m.get("dispositivo", "cpu"))


class Camara(threading.Thread):
    def __init__(self, cam: dict, cfg: dict, perceptor, publicador: Publicador, parar: threading.Event,
                 video_depuracion: str | None = None):
        super().__init__(daemon=True, name=cam["id"])
        self.cam, self.cfg, self.perceptor, self.pub, self.parar = cam, cfg, perceptor, publicador, parar
        self.zonas = zonas_desde_config(cam.get("zonas"))
        self.analizador = Analizador(cam["id"], self.zonas, Parametros(**cfg.get("parametros", {})))
        self.seguidor = Seguidor()
        c = cfg.get("clips", {})
        fps = cfg.get("fps_analisis", 10)
        self.grabador = Grabador(Path(c.get("carpeta", "datos/clips")) / cam["id"], c.get("antes", 6), c.get("despues", 4),
                                 fps, c.get("difuminar_caras", False))
        self.fuente = Fuente(cam["fuente"], fps, tiempo_real=cam.get("tiempo_real", False))
        self.video_depuracion = video_depuracion
        self.estado = {"id": cam["id"], "nombre": cam.get("nombre", cam["id"]), "en_linea": False, "fps": 0.0, "personas": 0}
        self.eventos_vivos: dict[str, dict] = {}
        self.con_clip: set[str] = set()  # eventos cuyo clip ya se envió: las actualizaciones van sin clip

    def run(self):
        escritor, n, t0 = None, 0, time.time()
        try:
            for t, img in self.fuente:
                if self.parar.is_set():
                    break
                f = self.perceptor(img, t)
                self.seguidor.actualizar(f.personas)
                for ev in self.analizador.actualizar(f):
                    datos = evento_a_dict(ev, reloj_real=not self.fuente.es_archivo)
                    if ev.evento_id in self.con_clip:
                        self.pub.publicar(datos, None)  # p. ej. «sale sin pasar por caja»: sube prioridad, mismo clip
                    else:
                        self.eventos_vivos[ev.evento_id] = datos
                        self.grabador.pedir(ev.evento_id, ev.track_id, t)
                    log.warning("[%s] %s · prioridad %s (%.2f)", self.cam["id"], ev.titulo, ev.prioridad, ev.puntuacion)
                for ev_id, clip in self.grabador.anadir(t, img, f):
                    self.pub.publicar(self.eventos_vivos.pop(ev_id), clip)
                    self.con_clip.add(ev_id)
                if self.video_depuracion:
                    dib = dibujar.esqueletos(dibujar.zonas(img.copy(), self.zonas), f)
                    if escritor is None:
                        h, w = dib.shape[:2]
                        escritor = cv2.VideoWriter(self.video_depuracion, cv2.VideoWriter_fourcc(*"mp4v"),
                                                   self.cfg.get("fps_analisis", 10), (w, h))
                    escritor.write(dib)
                n += 1
                self.estado.update(en_linea=True, personas=len(f.personas), fps=round(n / max(1e-6, time.time() - t0), 1))
        except Exception as e:
            log.error("[%s] parada: %s", self.cam["id"], e)
        finally:
            self.estado["en_linea"] = False
            for ev_id, datos in self.eventos_vivos.items():  # al cerrar, manda lo que quede (sin clip completo)
                self.pub.publicar(datos, None)
            if escritor:
                escritor.release()


def ejecutar(args):
    cfg = cargar_config(args.config)
    perceptor = crear_perceptor(cfg)
    api = cfg.get("api", {})
    pub = Publicador(api.get("url"), api.get("token"), cfg.get("cola", "datos/cola"))
    parar = threading.Event()
    hilos = [Camara(c, cfg, perceptor, pub, parar, args.video_depuracion) for c in cfg["camaras"]]
    for h in hilos:
        log.info("Cámara %s → %s", h.cam["id"], oculta_clave(h.cam["fuente"]))
        h.start()
    try:
        while any(h.is_alive() for h in hilos):
            pub.latido([h.estado for h in hilos])
            pub.reintentar_cola()
            time.sleep(10)
    except KeyboardInterrupt:
        parar.set()
    pub.latido([h.estado for h in hilos])


def demo(args):
    """Sistema completo con escenarios SINTÉTICOS: dibuja los esqueletos como vídeo, los analiza, graba clips y los
    envía a la API. Sirve para ver el producto funcionando de punta a punta sin cámaras."""
    nombres = list(sintetico.escenarios()) if args.escenario == "todos" else [args.escenario]
    pub = Publicador(args.api, args.token, "datos/cola")
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    for nombre in nombres:
        desc, avisa, frames = sintetico.generar(nombre, ruido=3, semilla=1)
        cam_id = args.camara
        an = Analizador(cam_id, sintetico.ZONAS)
        grab = Grabador(salida / "clips", antes=6, despues=4, fps=sintetico.FPS)
        vivos, con_clip, avisos = {}, set(), set()
        video = cv2.VideoWriter(str(salida / f"{nombre}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), sintetico.FPS,
                                (sintetico.ANCHO, sintetico.ALTO))
        for f in frames:
            img = dibujar.lienzo_sintetico(sintetico.ANCHO, sintetico.ALTO)
            dibujar.zonas(img, sintetico.ZONAS)
            dibujar.esqueletos(img, f, color_normal=(70, 60, 50))
            for ev in an.actualizar(f):
                datos = {**evento_a_dict(ev, reloj_real=False), "simulacion": True, "escenario": nombre}
                avisos.add(ev.evento_id)
                if ev.evento_id in con_clip:
                    pub.publicar(datos, None)
                else:
                    vivos[ev.evento_id] = datos
                    grab.pedir(ev.evento_id, ev.track_id, f.t)
            for ev_id, clip in grab.anadir(f.t, img, f):
                pub.publicar(vivos.pop(ev_id), clip)
                con_clip.add(ev_id)
            video.write(img)
        for ev_id, datos in vivos.items():
            pub.publicar(datos, None)
        video.release()
        print(f"{'⚠' if avisos else '·'} {nombre}: {desc} → {len(avisos)} alerta(s) (esperado: {'sí' if avisa else 'no'})")


def volcar_poses(args):
    cfg = cargar_config(args.config) if args.config else {}
    perceptor = crear_perceptor(cfg)
    seg = Seguidor()
    n = 0
    with open(args.salida, "w", encoding="utf-8") as fh:
        for t, img in Fuente(args.video, cfg.get("fps_analisis", 10)):
            f = perceptor(img, t)
            seg.actualizar(f.personas)
            fh.write(json.dumps(fotograma_a_dict(f)) + "\n")
            n += 1
    print(f"{n} fotogramas → {args.salida}")


def evaluar_cmd(args):
    if args.tipo == "sintetico":
        inf = evaluar.evaluar_sintetico(semillas=args.semillas)
    else:
        cfg = cargar_config(args.config)
        cam = cfg["camaras"][0]
        zonas = zonas_desde_config(cam.get("zonas"))
        if args.poses:
            fabrica = lambda video: PerceptorReproduccion(str(Path(args.poses) / (Path(video).stem + ".jsonl"))).fotogramas
        else:
            perceptor = crear_perceptor(cfg)
            fabrica = lambda video: (perceptor(img, t) for t, img in Fuente(video, cfg.get("fps_analisis", 10)))
        inf = evaluar.evaluar_videos(args.etiquetas, fabrica, zonas, Parametros(**cfg.get("parametros", {})))
    evaluar.imprimir(inf)
    if args.informe:
        evaluar.guardar(inf, args.informe)


def captura(args):
    for _, img in Fuente(args.fuente, 1):
        cv2.imwrite(args.salida, img)
        print(f"Captura guardada en {args.salida} ({img.shape[1]}×{img.shape[0]})")
        return


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(prog="vigilado-edge", description="Motor de visión de Vigilado (equipo de la tienda)")
    sub = ap.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("ejecutar"); p.add_argument("--config", required=True); p.add_argument("--video-depuracion")
    p.set_defaults(fn=ejecutar)
    p = sub.add_parser("demo"); p.add_argument("--escenario", default="todos"); p.add_argument("--api")
    p.add_argument("--token"); p.add_argument("--camara", default="cam-demo"); p.add_argument("--salida", default="datos/demo")
    p.set_defaults(fn=demo)
    p = sub.add_parser("volcar-poses"); p.add_argument("--video", required=True); p.add_argument("--salida", required=True)
    p.add_argument("--config"); p.set_defaults(fn=volcar_poses)
    p = sub.add_parser("evaluar"); p.add_argument("tipo", choices=["sintetico", "videos"]); p.add_argument("--semillas", type=int, default=10)
    p.add_argument("--etiquetas"); p.add_argument("--config"); p.add_argument("--poses"); p.add_argument("--informe")
    p.set_defaults(fn=evaluar_cmd)
    p = sub.add_parser("captura"); p.add_argument("--fuente", required=True); p.add_argument("--salida", default="captura.jpg")
    p.set_defaults(fn=captura)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
