"""Fuentes de vídeo: archivo de vídeo o cámara RTSP (IP, NVR o DVR: Hikvision, Dahua…).

Ejemplos de URL RTSP habituales (comprobar en cada equipo; cambian según modelo y firmware):
  Hikvision:  rtsp://usuario:clave@IP:554/Streaming/Channels/101   (101 = canal 1, flujo principal; 102 = secundario)
  Dahua:      rtsp://usuario:clave@IP:554/cam/realmonitor?channel=1&subtype=0   (subtype 0 = principal)
Usar el flujo PRINCIPAL: en el secundario (p. ej. 640×360) las manos quedan en pocos píxeles y la pose falla.
"""
from __future__ import annotations

import logging
import os
import time

import cv2

log = logging.getLogger("vigilado.fuente")
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")  # TCP: menos imágenes rotas que UDP


def oculta_clave(url: str) -> str:
    """Para logs: rtsp://usuario:clave@host → rtsp://usuario:***@host"""
    if "://" in url and "@" in url:
        esquema, resto = url.split("://", 1)
        cred, host = resto.split("@", 1)
        return f"{esquema}://{cred.split(':')[0]}:***@{host}"
    return url


class Fuente:
    """Itera (t, imagen) a la frecuencia de análisis pedida. Reconecta sola si una cámara se cae."""

    def __init__(self, url: str, fps_analisis: float = 10.0, tiempo_real: bool = False):
        self.url = url
        self.es_archivo = not url.lower().startswith(("rtsp://", "rtmp://", "http://", "https://"))
        self.fps_analisis = fps_analisis
        self.tiempo_real = tiempo_real
        self.cap = None
        self.fps_origen = 0.0

    def _abrir(self):
        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            raise ConnectionError(f"No se puede abrir {oculta_clave(self.url)}")
        self.fps_origen = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        log.info("Abierta %s (%.1f fps)", oculta_clave(self.url), self.fps_origen)

    def __iter__(self):
        espera = 1.0
        n = 0
        ultimo_t = -1e9
        inicio_real = time.time()
        while True:
            if self.cap is None:
                try:
                    self._abrir()
                    espera = 1.0
                except ConnectionError as e:
                    if self.es_archivo:
                        raise
                    log.warning("%s. Reintento en %.0f s", e, espera)
                    time.sleep(espera)
                    espera = min(espera * 2, 30)
                    continue
            ok, imagen = self.cap.read()
            if not ok:
                if self.es_archivo:
                    return
                log.warning("Se ha perdido la señal de %s; reconectando", oculta_clave(self.url))
                self.cap.release()
                self.cap = None
                continue
            t = n / self.fps_origen if self.es_archivo else time.time()
            n += 1
            if t - ultimo_t < 1.0 / self.fps_analisis - 1e-6:
                continue  # analizamos a fps_analisis, no a los fps de la cámara
            ultimo_t = t
            if self.es_archivo and self.tiempo_real:
                retraso = t - (time.time() - inicio_real)
                if retraso > 0:
                    time.sleep(retraso)
            yield t, imagen
