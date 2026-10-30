# Privacidad y cumplimiento

> Esto es un resumen técnico, **no asesoramiento jurídico**. Antes de vender, un abogado especializado debe revisar el
> encaje en RGPD, LOPDGDD y el Reglamento europeo de IA.

## Marco

- **RGPD + LOPDGDD (art. 22):** cartel informativo en el acceso; supresión de las imágenes en **1 mes como máximo**,
  salvo las que acrediten hechos.
- **Trabajadores (art. 89 LOPDGDD):** si las cámaras les graban, hay que informarles previamente.
- **AEPD (advertencias de octubre de 2026 sobre videovigilancia con IA):** la necesidad y proporcionalidad se analizan
  **por cada función de IA**, no solo por la cámara; protección de datos desde el diseño; régimen reforzado si hay biometría.
- **Papeles:** el comercio es **responsable**; Vigilado es **encargado del tratamiento** (contrato del art. 28 RGPD).

## Lo que ya hace el producto

| Medida | Dónde |
|---|---|
| Sin reconocimiento facial ni identificación biométrica (solo esqueleto y cajas) | `edge/vigilado_edge/percepcion.py` |
| Procesamiento local: el directo no sale de la tienda, solo clips de alertas | `edge/` |
| Alertas redactadas como «compatible con… revisar», nunca como acusación | `tipos.py`, panel |
| Explicación paso a paso de cada alerta (revisable y discutible) | `analizador.py`, panel |
| Retención automática ≤ 30 días; se conservan solo los incidentes confirmados | `api/app/principal.py` (`purgar_clips`) |
| Registro de accesos (quién vio qué clip y cuándo) | API `/registro`, panel |
| Roles y aislamiento por empresa | API |
| Enlaces de clip firmados de 5 min; sesiones fuera de URLs | API + panel |
| Difuminado opcional de cabezas en clips | `clips.difuminar_caras` en la config |
| Contraseñas bcrypt, tokens de equipo como hash | `api/app/seguridad.py` |

## Pendiente antes de vender

- [ ] Revisión jurídica (RGPD, LOPDGDD, Reglamento de IA) y decisión sobre difuminado por defecto.
- [ ] Plantilla de contrato de encargado del tratamiento.
- [ ] Plantilla de evaluación de impacto (EIPD) por tienda y por función.
- [ ] Cartel informativo y texto de información a trabajadores.
- [ ] Alojamiento en la UE, cifrado del disco de clips y copias de seguridad.
- [ ] HTTPS obligatorio en producción (proxy inverso) y rotación de tokens de equipo.
