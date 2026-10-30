"""WebSockets: el panel recibe las alertas al instante. Cada conexión solo ve las de su organización."""
from __future__ import annotations

import json

from fastapi import WebSocket


class Difusor:
    def __init__(self):
        self.conexiones: dict[str, set[WebSocket]] = {}

    def registrar(self, org: str, ws: WebSocket):
        self.conexiones.setdefault(org, set()).add(ws)

    def desconectar(self, org: str, ws: WebSocket):
        self.conexiones.get(org, set()).discard(ws)

    async def enviar(self, org: str, mensaje: dict):
        texto = json.dumps(mensaje, default=str, ensure_ascii=False)
        for ws in list(self.conexiones.get(org, set())):
            try:
                await ws.send_text(texto)
            except Exception:
                self.desconectar(org, ws)


difusor = Difusor()
