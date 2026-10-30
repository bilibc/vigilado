# Arquitectura

```
TIENDA (mini PC)                                          NUBE (UE)
┌───────────────────────────────────────────┐            ┌──────────────────────────────┐
│ Cámaras / NVR ──RTSP──► fuente.py          │            │ API FastAPI (api/app)        │
│   (flujo principal, TCP, reconexión)       │            │  · /edge/eventos  /latido    │
│                  ▼                         │  HTTPS     │  · alertas, roles, registro  │
│ percepcion.py  YOLOX + RTMPose (rtmlib)    │ ─────────► │  · WebSocket al panel        │
│                  ▼                         │ solo       │  · purga de clips (30 días)  │
│ seguimiento.py  track_id por persona       │ alertas    │ PostgreSQL · clips (disco UE)│
│                  ▼                         │ + clip     │ Panel React (panel/)         │
│ analizador.py  coge → oculta → contexto    │            └──────────────────────────────┘
│                  ▼                         │
│ clips.py  búfer 6 s + 4 s → MP4 H.264      │
│ publicador.py  envío con cola sin conexión │
└───────────────────────────────────────────┘
```

## Flujo de una alerta

1. `fuente.py` lee la cámara y entrega imágenes a 10 fps (no hace falta analizar los 25 fps).
2. `percepcion.py` devuelve personas con 17 puntos del esqueleto.
3. `seguimiento.py` mantiene la identidad de cada persona entre fotogramas (`track_id`, sin identificar a nadie).
4. `analizador.py` busca la secuencia: **coge** (muñeca entra y sale de una estantería) → **oculta** (mano en
   bolsillo/cintura con el codo doblado, o en la cintura bajo la ropa, durante ≥ 0,5 s, en los 6 s siguientes) →
   **contexto** (pasa por caja: baja la prioridad; sale sin pasar por caja: sube).
5. `clips.py` guarda un clip de 6 s antes + 4 s después, con la persona recuadrada.
6. `publicador.py` lo manda a la API. Las actualizaciones posteriores (p. ej. «sale sin pasar por caja») suben la
   prioridad sin cambiar el clip.
7. La API lo guarda y lo empuja al panel por WebSocket. El encargado lo revisa y lo marca.

## Decisiones técnicas

| Pieza | Elección | Motivo |
|---|---|---|
| Visión | Python + OpenCV/FFmpeg | Ecosistema de modelos; FFmpeg es el lector RTSP más robusto con NVR/DVR |
| Pose | RTMPose + YOLOX vía `rtmlib` (Apache 2.0) | Rápido en CPU/GPU con ONNX Runtime. **No** Ultralytics (AGPL-3.0 obliga a licencia comercial) |
| Seguimiento | IoU voraz propio | Suficiente para el MVP; cambio previsto a ByteTrack (MIT) cuando haya vídeo con cruces |
| Reglas antes que red neuronal | Capa 1 explicable | Sin datos propios no se puede entrenar bien; las reglas son medibles, ajustables y explicables al cliente |
| API | FastAPI + SQLAlchemy | Asíncrono, WebSockets, validación con Pydantic |
| BD | PostgreSQL (SQLite en desarrollo) | Relacional multi-empresa, transacciones, maduro |
| Panel | React + Vite + TS | App privada tras login: no necesita SSR/SEO de Next.js; más simple de mantener |
| Clips | H.264 + faststart | Se reproduce en cualquier navegador sin plugins |
| Despliegue | Docker / docker compose | Igual en cada tienda y en la nube |

## Seguridad aplicada

- Contraseñas con bcrypt; sesiones JWT con caducidad; tokens de equipo guardados solo como hash SHA-256.
- Aislamiento por organización en cada consulta (probado en `api/tests`).
- Roles: propietario, encargado, lectura.
- Clips con **enlace firmado de 5 minutos y de un solo clip**; la sesión nunca viaja en URLs (tampoco en el WebSocket).
- Registro de accesos: inicio de sesión, cada visionado de clip, cada revisión, altas y borrados.
- Retención automática de clips (≤ 30 días; se conservan los de incidentes confirmados).

## Próximas capas de IA (cuando haya datos)

- **Capa 2:** clasificador temporal sobre secuencias de pose (PoseC3D / ST-GCN), entrenado con PoseLift + grabaciones propias.
- **Capa 3:** verificador sobre el clip (modelo de acción en vídeo) solo en candidatos, para descartar falsas alarmas.
- **Bolsas y mochilas:** detector de objetos con licencia comercial compatible; el analizador ya acepta `objetos`.
