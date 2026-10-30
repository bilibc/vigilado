"""Clips de alerta: guarda los últimos segundos de cada cámara y, cuando hay evento, escribe un MP4 de
`antes` segundos previos + `despues` posteriores. El vídeo en directo nunca sale de la tienda: solo estos clips."""
from __future__ import annotations

import logging
import shutil
import subprocess
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2

from . import dibujar
from .tipos import Fotograma

log = logging.getLogger("vigilado.clips")


@dataclass
class _Pendiente:
    evento_id: str
    track_id: int
    fin: float
    fotogramas: list = field(default_factory=list)


class Grabador:
    def __init__(self, carpeta: str, antes: float = 6.0, despues: float = 4.0, fps: float = 10.0,
                 difuminar_caras: bool = False):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.antes, self.despues, self.fps = antes, despues, fps
        self.difuminar = difuminar_caras
        self.buffer: deque = deque()
        self.pendientes: dict[str, _Pendiente] = {}

    def anadir(self, t: float, imagen, f: Fotograma) -> list[tuple[str, Path]]:
        """Añade un fotograma. Devuelve [(evento_id, ruta_clip)] de los clips que se han terminado ahora."""
        self.buffer.append((t, imagen, f))
        while self.buffer and t - self.buffer[0][0] > self.antes:
            self.buffer.popleft()
        terminados = []
        for ev_id, p in list(self.pendientes.items()):
            p.fotogramas.append((t, imagen, f))
            if t >= p.fin:
                terminados.append((ev_id, self._escribir(p)))
                del self.pendientes[ev_id]
        return terminados

    def pedir(self, evento_id: str, track_id: int, t: float):
        """Empieza (o alarga) el clip de un evento."""
        if evento_id in self.pendientes:
            self.pendientes[evento_id].fin = max(self.pendientes[evento_id].fin, t + self.despues)
            return
        self.pendientes[evento_id] = _Pendiente(evento_id, track_id, t + self.despues, list(self.buffer))

    def _escribir(self, p: _Pendiente) -> Path:
        ruta = self.carpeta / f"{p.evento_id}.mp4"
        imgs = []
        for _, img, f in p.fotogramas:
            img = img.copy()
            if self.difuminar:
                dibujar.difuminar_cabezas(img, f)
            dibujar.destacar_caja(img, f, p.track_id)
            imgs.append(img)
        if not imgs:
            return ruta
        h, w = imgs[0].shape[:2]
        if shutil.which("ffmpeg"):
            # H.264 + faststart: se reproduce directamente en cualquier navegador
            cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                   "-r", str(self.fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(ruta)]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for img in imgs:
                proc.stdin.write(img.tobytes())
            proc.stdin.close()
            proc.wait()
        else:  # sin ffmpeg: mp4v (puede no verse en algunos navegadores)
            out = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), self.fps, (w, h))
            for img in imgs:
                out.write(img)
            out.release()
        log.info("Clip guardado: %s (%d fotogramas)", ruta, len(imgs))
        return ruta
