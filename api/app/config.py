"""Configuración por variables de entorno."""
from __future__ import annotations

import os
import secrets
from pathlib import Path


class Ajustes:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./datos/vigilado.db")
        self.secreto = os.getenv("VIGILADO_SECRETO") or secrets.token_hex(32)
        self.carpeta_clips = Path(os.getenv("VIGILADO_CLIPS", "./datos/clips"))
        # LOPDGDD art. 22.3: las imágenes se suprimen en un mes como máximo (salvo las que acreditan hechos).
        self.retencion_dias = min(int(os.getenv("VIGILADO_RETENCION_DIAS", "30")), 30)
        self.minutos_sesion = int(os.getenv("VIGILADO_MINUTOS_SESION", "720"))
        self.origenes_cors = [o for o in os.getenv("VIGILADO_CORS", "http://localhost:5173").split(",") if o]
        self.carpeta_panel = os.getenv("VIGILADO_PANEL", "")
        if not os.getenv("VIGILADO_SECRETO"):
            print("AVISO: VIGILADO_SECRETO no definido; se usa uno temporal (las sesiones caducan al reiniciar).")


ajustes = Ajustes()
