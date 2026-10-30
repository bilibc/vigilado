# Vigilado — notas para Claude Code

Videovigilancia con IA para comercios: avisa de secuencias de gestos compatibles con ocultación (coge → oculta → sale)
para que una persona revise el vídeo. Sin biometría, sin reconocimiento facial, procesamiento local en la tienda.
Dueño del proyecto: Mario (habla en español de España, respuestas cortas y al grano, datos reales, sin inventar).

## Estructura
- `edge/` motor de la tienda (Python): fuente RTSP/vídeo → pose (rtmlib: YOLOX + RTMPose) → seguimiento →
  `analizador.py` (reglas, umbrales en `Parametros`) → clips → publicador a la API.
- `api/` FastAPI + SQLAlchemy (SQLite en desarrollo, PostgreSQL en producción). Sirve el panel si `VIGILADO_PANEL`.
- `panel/` React + Vite + TS. `npm run build:demo` genera la demo con datos de ejemplo (`src/demo.ts`).
- `docs/` análisis, arquitectura, privacidad, protocolo de pruebas y hoja de ruta.

## Comandos
- Tests: `cd edge && python -m pytest -q` · `cd api && python -m pytest -q` · `cd panel && npm run build`
- Evaluación lógica: `cd edge && python -m vigilado_edge evaluar sintetico`
- Demo de punta a punta: ver README («Probarlo en local»).

## Reglas del proyecto
- Nunca presentar una alerta como acusación: «Posible ocultación», «revisa el vídeo».
- No usar Ultralytics/YOLO (AGPL-3.0). Modelos con licencia comercial compatible.
- Nada de biometría ni identificación de personas.
- No ajustar umbrales para «aprobar» los escenarios sintéticos: se ajustan con vídeo real medido (`docs/pruebas.md`).
- Retención de clips ≤ 30 días (LOPDGDD art. 22). La sesión nunca va en URLs.
- Panel: lenguaje llano, mínimo de datos, colores siempre por variables (`--tinta`, `--fondo`…) para claro y oscuro.

## Estado (30-oct-2026)
Hecho y probado: analizador (sintético), API, panel, demo publicada.
SIN probar todavía: modelo de pose con vídeo real, cámara RTSP real, Docker.
Siguiente paso: grabar 10–20 escenas con el móvil, pasar por el modelo en un portátil con internet
(`pip install -r edge/requirements-modelo.txt`), etiquetar y medir (`vigilado-edge evaluar videos`).
Pendiente de producto: editor de zonas en el panel, avisos al móvil, revisión jurídica.
