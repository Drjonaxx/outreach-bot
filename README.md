# outreach-bot

Kit para salir a vender **Clara**, la coordinadora con IA para clínicas
estéticas (el producto vive en su propio repositorio, `clara`).

## Qué hay aquí

| Archivo | Qué es |
|---|---|
| `prospectos/clinicas-pr.csv` | 39 med spas y clínicas estéticas de Puerto Rico con su teléfono, email cuando es público, web y la fuente de cada dato. Prioridad A, B o C. |
| `mensajes/entrevista.md` | **Fase 1, la de ahora.** Mensajes para pedir la entrevista, las cinco preguntas, el cierre y la regla de decisión. Sin demo. |
| `mensajes/oferta-servicio.md` | Paquetes y precios para instalar y mantener la recepción digital de una clínica con WhatsApp Business y el AI Concierge de Fresha. |
| `mensajes/plantillas.md` | Los mensajes para vender Clara. En pausa hasta que las entrevistas digan si vale la pena. |

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

## Meta de las próximas cuatro semanas

1. Semana 1: 10 entrevistas con clínicas de prioridad A, sin vender ni enseñar
   la demo.
2. Semana 2: decidir con la regla de `mensajes/entrevista.md` y volver con una
   propuesta a quienes aceptaron una segunda reunión.
3. Semanas 3 y 4: instalar a las primeras dos o tres clínicas cobrando 50% por
   adelantado.
4. Día 30: si nadie ha pagado nada, parar.
