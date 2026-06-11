# Análisis IA Diario 🧠

Web app (PWA) que muestra un análisis diario de las noticias de IA, generado por
**Claude** a través de un escenario de **Make.com**.

## Cómo funciona

```
App (navegador)  →  Webhook de Make  →  RSS The Decoder  →  Claude  →  Reporte
```

La app es 100% estática (HTML/CSS/JS). Toda la lógica vive en el escenario de Make:
1. Recibe la petición del webhook.
2. Descarga las noticias de IA de The Decoder (vía rss2json).
3. Envía los titulares a Claude (Sonnet 4.6) para analizarlos.
4. Devuelve el reporte ejecutivo en español directamente en la respuesta.

## Archivos

| Archivo | Función |
|---------|---------|
| `index.html` | Interfaz de la app |
| `app.js` | Lógica: llama al webhook y renderiza el reporte (markdown) |
| `manifest.json` | Configuración PWA (instalable en el teléfono) |
| `sw.js` | Service worker (cache + offline) |
| `icon-192.png`, `icon-512.png` | Íconos de la app |

## Probar localmente

```bash
python3 -m http.server 8099
# abre http://localhost:8099
```

## Publicar (gratis)

Cualquiera de estas opciones sirve, subiendo esta carpeta:
- **Netlify**: arrastra la carpeta en https://app.netlify.com/drop
- **Vercel**: `vercel` en la carpeta, o conecta el repo
- **GitHub Pages**: activa Pages sobre esta rama/carpeta

Una vez publicada con HTTPS, podrás **instalarla** en el teléfono
(Android: botón "Instalar"; iPhone: Compartir → "Añadir a inicio").

## Configuración

La URL del webhook está en `app.js`:

```js
const WEBHOOK_URL = "https://hook.us2.make.com/...";
```
