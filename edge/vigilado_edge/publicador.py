"""Envía los eventos (y su clip) a la API. Si no hay conexión, los guarda en cola y los reintenta."""
from __future__ import annotations

import json
import logging
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .tipos import Evento

log = logging.getLogger("vigilado.publicador")


def evento_a_dict(ev: Evento, reloj_real: bool) -> dict:
    """reloj_real: si t son segundos epoch (cámara en vivo) o segundos desde el inicio de un vídeo."""
    def ts(t):
        if reloj_real:
            return datetime.fromtimestamp(t, timezone.utc).isoformat()
        return datetime.now(timezone.utc).isoformat()

    return {
        "evento_id": ev.evento_id, "camara_id": ev.camara_id, "track_id": ev.track_id, "tipo": ev.tipo,
        "titulo": ev.titulo, "puntuacion": ev.puntuacion, "prioridad": ev.prioridad,
        "inicio": ts(ev.inicio), "actualizado": ts(ev.actualizado),
        "pasos": [{"t": round(p.t - ev.inicio, 2), "tipo": p.tipo, "texto": p.texto, "datos": p.datos} for p in ev.pasos],
    }


def _multipart(campos: dict, archivo: Path | None):
    limite = uuid.uuid4().hex
    partes = []
    for k, v in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    if archivo and archivo.exists():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="clip"; filename="{archivo.name}"\r\n'
                      f"Content-Type: video/mp4\r\n\r\n".encode() + archivo.read_bytes() + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


class Publicador:
    def __init__(self, url_api: str | None, token: str | None, carpeta_cola: str = "datos/cola"):
        self.url = (url_api or "").rstrip("/")
        self.token = token
        self.cola = Path(carpeta_cola)
        self.cola.mkdir(parents=True, exist_ok=True)

    def publicar(self, datos: dict, clip: Path | None = None) -> bool:
        if not self.url:
            log.info("Evento (sin API configurada): %s", json.dumps(datos, ensure_ascii=False))
            return True
        try:
            cuerpo, tipo = _multipart({"datos": json.dumps(datos, ensure_ascii=False)}, clip)
            req = urllib.request.Request(f"{self.url}/api/v1/edge/eventos", data=cuerpo, method="POST",
                                         headers={"Content-Type": tipo, "Authorization": f"Bearer {self.token}"})
            with urllib.request.urlopen(req, timeout=15) as r:
                r.read()
            return True
        except Exception as e:  # sin red, API caída…
            log.warning("No se pudo enviar el evento %s (%s); queda en cola", datos.get("evento_id"), e)
            nombre = f"{int(time.time() * 1000)}-{datos['evento_id']}"
            (self.cola / f"{nombre}.json").write_text(json.dumps({"datos": datos, "clip": str(clip) if clip else None}))
            return False

    def reintentar_cola(self):
        for f in sorted(self.cola.glob("*.json")):
            d = json.loads(f.read_text())
            f.unlink()
            if not self.publicar(d["datos"], Path(d["clip"]) if d.get("clip") else None):
                break  # sigue sin red: lo ha vuelto a encolar

    def latido(self, camaras: list[dict]):
        if not self.url:
            return
        try:
            req = urllib.request.Request(f"{self.url}/api/v1/edge/latido", method="POST",
                                         data=json.dumps({"camaras": camaras}).encode(),
                                         headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"})
            urllib.request.urlopen(req, timeout=5).read()
        except Exception as e:
            log.debug("Latido fallido: %s", e)
