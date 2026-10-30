# Cómo medir si funciona (sin engañarnos)

La lógica ya está probada con escenarios sintéticos. Lo que falta es **medir con vídeo real**. Este es el protocolo.

## 1. Primera prueba barata: tu móvil como cámara

1. Graba con el móvil, fijo en alto (como una cámara de techo inclinada, 2–2,5 m), una estantería de casa.
2. Representa escenas de 20–40 s, cada una en un vídeo:
   - **Ocultación:** coger un objeto y meterlo en el bolsillo / en la cintura bajo la camiseta / en una mochila.
   - **Legítimas:** sacar el móvil del bolsillo sin coger nada; coger y dejarlo en una cesta; coger, mirar y devolver;
     coger y llevarlo en la mano; pasar sin tocar.
3. Alternativa en directo: apps tipo «IP Webcam» (Android) convierten el móvil en cámara IP; su URL se pone como `fuente`.

## 2. Etiquetar

`etiquetas.csv` (segundos desde el inicio de cada vídeo):

```
video,inicio_s,fin_s,tipo
oculta_bolsillo_01.mp4,8.0,12.5,ocultacion
movil_sin_coger_01.mp4,0,0,normal
```

## 3. Medir

```bash
cd edge
# opcional: volcar las poses una vez y re-evaluar reglas sin GPU
python -m vigilado_edge volcar-poses --video ../muestras/oculta_bolsillo_01.mp4 --salida poses/oculta_bolsillo_01.jsonl
python -m vigilado_edge evaluar videos --etiquetas etiquetas.csv --config config.yaml [--poses poses] --informe informe.json
```

Salida: **sensibilidad** (ocultaciones detectadas), **precisión** (alertas que eran reales) y **falsas alarmas por hora**.

## 4. Objetivos para pasar a piloto (provisionales, a validar)

| Métrica | Objetivo | Por qué |
|---|---|---|
| Falsas alarmas | ≤ 1 por cámara y 8 h de apertura | Si molesta, el comercio lo apaga |
| Sensibilidad en escenas representadas | ≥ 70 % | Suficiente para que el cliente vea valor; mejora con datos |
| Pose visible | Muñecas detectadas en ≥ 80 % de los fotogramas de la zona | Si no, la cámara no sirve (ángulo/resolución) |

## 5. Para el piloto en tienda

- Grabaciones con actores y **consentimiento firmado**; cartel informativo; nada de clientes reales en las pruebas.
- Medir por separado cada cámara: el ángulo cambia mucho los resultados.
- Guardar todo informe en `docs/informes/` con fecha, cámara y versión.
