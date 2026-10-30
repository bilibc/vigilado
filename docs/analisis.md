# Análisis de viabilidad (octubre 2026)

## Mercado y competencia

- **Veesion** (París) hace exactamente esto: reconocimiento de gestos de hurto sobre las cámaras existentes, avisos al
  personal. **España es su tercer mercado mundial** y cerró una ronda de 38 M€. Hay reseñas que mencionan falsas
  alarmas y alarmas perdidas según la distribución de la tienda.
- Conclusión: el mercado existe y paga. No se gana copiando: se entra por **comercio pequeño e independiente**,
  precio claro, instalación en el día, soporte cercano en español y procesamiento 100 % local.

## Qué es realista con la tecnología actual

| Objetivo | Realista |
|---|---|
| Detectar y seguir personas | Sí (maduro) |
| Pose (muñecas, codos, caderas) | Sí, si la cámara no es muy cenital y hay resolución |
| Secuencia coge → oculta → sale como «revisar» | Sí, con falsas alarmas al principio |
| Distinguir producto propio vs. de la tienda | No al principio; mejora con datos propios |
| Funcionar sin configurar cada tienda | No: cada cámara necesita sus zonas |

## Datos

- **PoseLift** (WACV 2025): hurtos reales en tienda, solo poses. Comprobar licencia antes de uso comercial.
- **RetailS** (arXiv 2026): poses, multicámara, escenificados y reales.
- **UCF-Crime**: categoría de hurto; solo investigación.
- La ventaja competitiva a largo plazo son **los datos propios**: grabaciones con actores y alertas revisadas por clientes.

## Riesgos principales

1. Ángulo y resolución de cámaras existentes (manos de pocos píxeles).
2. Falsas alarmas: la métrica que decide si el cliente se queda.
3. Datos para las capas aprendidas.
4. Coste de GPU por tienda (afecta al precio).
5. Encaje legal (ver `privacidad.md`).

## Fuentes

- Alimarket: Veesion cierra una ronda de 38 M€ — https://www.alimarket.es/alimentacion/noticia_amp/408570/veesion-cierra-una-ronda-de-financiacion-de-38-m--para-impulsar-soluciones-de-ia-en-antihurto
- RFP.wiki: reseñas de Veesion — https://www.rfp.wiki/vendors/veesion
- PoseLift (WACV 2025) — https://openaccess.thecvf.com/content/WACV2025W/ASTAD/html/Rashvand_Exploring_Pose-Based_Anomaly_Detection_for_Retail_Security_A_Real-World_Shoplifting_WACVW_2025_paper.html
- RetailS (arXiv 2603.04723) — https://arxiv.org/html/2603.04723v1
- AEPD: garantías para incorporar IA a la videovigilancia — https://www.aepd.es/prensa-y-comunicacion/notas-de-prensa/aepd-sennala-garantias-para-incorporar-ia-a-sistemas-videovigilancia
