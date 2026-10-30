# Vigilado

Videovigilancia inteligente para comercios. Convierte las cámaras que la tienda ya tiene en un sistema que **avisa
cuando ve una secuencia de gestos compatible con la ocultación de un producto**, para que una persona lo revise.

- **No acusa a nadie.** Cada alerta dice «gesto compatible con ocultación — revisar» y explica paso a paso qué ha visto.
- **Sin reconocimiento facial ni biometría.** Solo puntos del esqueleto (muñecas, codos, hombros, caderas) y cajas.
- **El vídeo en directo no sale de la tienda.** Se analiza en un mini PC local; solo sube el clip de cada alerta.

## Estado (octubre 2026) — sin humo

| Parte | Estado |
|---|---|
| Analizador de secuencias (coge → oculta → sale, con casos legítimos) | ✅ Hecho y probado con escenarios sintéticos (con ruido) |
| Seguimiento de personas, clips, cola sin conexión, latido de cámaras | ✅ Hecho y probado |
| Lectura de cámaras RTSP (Hikvision, Dahua…) con reconexión | ✅ Hecho · ⚠️ **sin probar con una cámara real** |
| Modelo de pose real (YOLOX + RTMPose vía `rtmlib`) | ✅ Integrado · ⚠️ **sin probar**: se descarga en el primer arranque y este entorno de desarrollo no tenía acceso |
| API (alertas, tiempo real, roles, registro de accesos, retención 30 días) | ✅ Hecho y probado |
| Panel web (alertas en directo, vídeo, revisión, cámaras, estadísticas, usuarios) | ✅ Hecho y probado en navegador |
| **Precisión real con vídeo** | ❌ **Sin medir todavía.** Es el siguiente paso (ver `docs/pruebas.md`) |

Los escenarios sintéticos prueban que la **lógica** hace lo que debe. **No** prueban que el sistema detecte hurtos en una
tienda real: eso depende del modelo de pose con vídeo real, del ángulo de la cámara y de los umbrales, y se mide con
grabaciones etiquetadas.

## Estructura

```
edge/    Motor de visión (Python). Se ejecuta en el equipo de la tienda.
api/     API central (FastAPI + PostgreSQL/SQLite). Sirve también el panel.
panel/   Panel web (React + Vite + TypeScript).
docs/    Análisis, arquitectura, privacidad, pruebas y hoja de ruta.
tools/   Simulador de cámara RTSP y utilidades.
```

## Probarlo en local (sin cámaras)

```bash
# 1) API
cd api && pip install -r requirements-dev.txt
export VIGILADO_SECRETO=$(python3 -c "import secrets;print(secrets.token_hex(32))")
python -m app.sembrar --email tu@correo.es --clave "una-clave-larga"   # apunta el token del equipo
uvicorn app.principal:app --port 8000

# 2) Panel (otra terminal) → http://localhost:5173
cd panel && npm install && npm run dev

# 3) Demo de punta a punta con escenarios sintéticos (otra terminal)
cd edge && pip install -r requirements.txt
python -m vigilado_edge demo --api http://localhost:8000 --token vgl_EL_TOKEN --camara cam-perfumeria
```

En el panel aparecen las alertas al momento, con su clip, la explicación y los botones de revisión
(van marcadas como «Simulación»).

## Probarlo con vídeo de verdad

```bash
cd edge && pip install -r requirements-modelo.txt     # rtmlib + onnxruntime (la 1.ª vez descarga los modelos)
cp config.ejemplo.yaml config.yaml                     # fuente: un vídeo o rtsp://… y dibuja las zonas
python -m vigilado_edge ejecutar --config config.yaml --video-depuracion depuracion.mp4
```

`depuracion.mp4` muestra esqueletos y zonas: lo primero es comprobar que la pose se ve bien en esa cámara.

## Tests

```bash
cd edge && python -m pytest -q     # 21 tests: analizador, escenarios, clips, evaluación, cola
cd api  && python -m pytest -q     # 7 tests: sesión, aislamiento entre empresas, roles, tiempo real, retención
cd edge && python -m vigilado_edge evaluar sintetico
```
