# Hoja de ruta

| Fase | Contenido | Estado |
|---|---|---|
| 0 · Base | Repo, estructura, Docker, simulador RTSP | ✅ (Docker sin probar en el entorno de desarrollo) |
| 1 · Motor | Fuente RTSP/vídeo, pose (rtmlib), seguimiento, zonas, vídeo de depuración | ✅ código · ⚠️ falta probar con modelo y vídeo real |
| 2 · Eventos | Secuencia coge → oculta → contexto, puntuación, clips, cola | ✅ probado con escenarios sintéticos |
| 3 · Panel | API, BD, WebSocket, panel de alertas, cámaras, estadísticas, registro, usuarios | ✅ probado en navegador |
| 4 · Medición | Grabaciones propias etiquetadas, informe de precisión, ajuste de umbrales | ⏭️ **siguiente** |
| 5 · Piloto | 1–2 tiendas reales, mini PC instalado, cámaras reales | Pendiente |
| 6 · Producto | Editor de zonas en el panel, avisos al móvil, capas 2 y 3 de IA, bolsas, facturación, legal | Pendiente |

## Siguiente paso concreto

1. Instalar `requirements-modelo.txt` en un portátil con internet.
2. Grabar 10–20 escenas con el móvil (`docs/pruebas.md`).
3. Ejecutar con `--video-depuracion` y comprobar que la pose se ve bien.
4. Etiquetar y medir. Ajustar `Parametros` con los datos, no a ojo.
