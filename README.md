# outreach-bot

Kit para salir a vender **Clara**, la coordinadora con IA para clínicas
estéticas (el producto vive en su propio repositorio, `clara`).

## Qué hay aquí

| Archivo | Qué es |
|---|---|
| `prospectos/clinicas-pr.csv` | 39 med spas y clínicas estéticas de Puerto Rico con su teléfono, email cuando es público, web y la fuente de cada dato. Prioridad A, B o C, y columnas `estado` y `proximo_paso` para llevar el seguimiento. |
| `mensajes/plantillas.md` | Tres emails, un WhatsApp, un guion de llamada con objeciones, cómo hacer la visita y las reglas de cumplimiento. |

## Cómo se armó la lista

Con búsquedas públicas por pueblo y por servicio (med spa, Botox, sueroterapia,
pérdida de peso con GLP-1) en Infopáginas, Fresha, las webs de las clínicas y
directorios médicos, en octubre de 2026. La columna `confirmado_en` dice si el
teléfono salió en dos fuentes distintas o en una sola.

Antes de llamar, abre la web de la clínica y confirma el número. Las listas
públicas se desactualizan, y algunos emails (NUMED, Surgi Spa) están ocultos
en sus webs: se piden por teléfono.

**Prioridad A (16):** med spas con inyectables, láser, sueros o GLP-1. Reciben
muchos mensajes, cobran tickets altos y casi todas tienen horario limitado.
**B (21):** clínicas más pequeñas o más médicas. **C (2):** más salón que clínica.

## Meta de las dos primeras semanas

Cinco demos y dos pilotos. Para cada piloto: llenar `data/clinica.json` de
Clara con sus servicios y precios (una hora) y conectar su WhatsApp. Mientras
Meta aprueba el número, la clínica puede usar el chat de la web con un código
QR en recepción.
