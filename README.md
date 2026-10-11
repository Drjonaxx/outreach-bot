# clipper

Convierte un episodio largo de podcast en clips verticales listos para **YouTube Shorts** y **TikTok**:

1. **Descarga** el video (YouTube o cualquier sitio que soporte `yt-dlp`) o usa un archivo local.
2. **Transcribe** en español con Whisper (`faster-whisper`), con tiempos palabra por palabra.
3. **Elige los momentos virales** con Claude: busca ganchos fuertes, ideas que se entiendan solas y un buen remate, y escribe título, texto gancho, descripción y hashtags.
4. **Reencuadra a 9:16** siguiendo la cara de quien habla. Si hay un corte de cámara, el encuadre salta con él. En tomas amplias con dos personas usa plano completo con fondo desenfocado.
5. **Quema subtítulos animados**: 2-3 palabras grandes con la palabra activa en amarillo, más el texto gancho arriba.
6. **Normaliza el audio** a -14 LUFS (el estándar de redes) y exporta MP4 1080×1920 junto con un `.txt` para copiar y pegar al publicar.

## Instalación

Requisitos: Python 3.10+ y `ffmpeg` (compilado con libass, como casi todas las distribuciones).

```bash
# macOS: brew install ffmpeg     Ubuntu: sudo apt install ffmpeg     Windows: winget install ffmpeg
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...                 # Windows: set ANTHROPIC_API_KEY=...
```

La primera ejecución descarga el modelo de Whisper (desde HuggingFace) y el detector de caras YuNet (~230 KB, desde GitHub).

## Uso

```bash
clipper "https://www.youtube.com/watch?v=XXXX" --clips 6
```

Resultado en `out/<id-del-video>/`:

```
clip_01.mp4   clip_01.txt   ← video + título/descripción/hashtags para pegar
clip_02.mp4   clip_02.txt
clips.json                  ← los momentos elegidos (editable)
transcript.json             ← transcripción en caché
```

### Opciones útiles

| Opción | Para qué |
|---|---|
| `--clips 8` | máximo de clips por episodio |
| `--min 25 --max 75` | duración mínima y máxima en segundos |
| `--whisper-model medium` | mejor transcripción (más lenta). Con GPU NVIDIA: `large-v3 --device cuda` |
| `--context "Entrevista a X sobre finanzas"` | ayuda a Claude a elegir mejor |
| `--select-only` | solo transcribe y elige clips, sin renderizar (para revisar antes) |
| `--reselect` | vuelve a pedirle clips a Claude |
| `--font "Montserrat ExtraBold"` | otra fuente para subtítulos (debe estar instalada) |
| `--hook-seconds 4` | muestra el texto gancho solo los primeros 4 s (por defecto, todo el clip) |

### Flujo recomendado

1. `clipper URL --select-only` → revisa la lista de clips que imprime.
2. Si quieres ajustar alguno, edita `out/<id>/clips.json` (tiempos, título, gancho).
3. `clipper URL` → renderiza usando tu `clips.json`. La transcripción ya está en caché, así que no se repite.

## Costo aproximado

- Whisper corre local: gratis. En CPU, el modelo `small` tarda aproximadamente lo mismo que dura el episodio.
- Claude: una sola llamada por episodio. Un podcast de 1 h son unos 15-20k tokens de entrada, del orden de centavos de dólar.

## Antes de publicar: permisos

Subir clips de otros sin permiso puede traerte reclamos de copyright y strikes. Las opciones seguras son:

- **Programas de clipping**: muchos podcasters y streamers pagan por vistas a quienes recortan su contenido. Busca "content rewards" o "clipping campaigns" (Whop, el Discord del creador).
- **Pedir permiso directo** al podcast. A muchos les interesa la difusión gratis.
- **Dar crédito siempre.** El `.txt` ya incluye el nombre del episodio, el canal y el link.

YouTube desmonetiza el "contenido reutilizado" sin aporte propio. Los subtítulos, el gancho y la selección ayudan, pero no garantizan nada.

## Tests

```bash
pip install -e ".[dev]" && pytest
```

## Correrlo en GitHub Actions (sin computadora)

El workflow `.github/workflows/clipper.yml` corre el pipeline en los servidores de GitHub cada vez que cambia `job.json` o algo en `jobs/`:

1. Edita `job.json` con `name` (nombre de la carpeta) y `url`. Al hacer push, Actions descarga y transcribe. El resultado queda en la rama `claude/clipper-out`, en `<name>/transcript.json`.
2. Sube `jobs/<name>/clips.json` con los clips elegidos (a mano, con `clipper --select-only` o pidiéndoselo a Claude). El push dispara el render, y los `.mp4` y `.txt` aparecen en `claude/clipper-out/<name>/`.

Si YouTube pide verificación anti-bots desde los servidores de GitHub, exporta tus cookies de YouTube en formato Netscape y guárdalas en el secreto del repo `YT_COOKIES`.

> Localmente, yt-dlp necesita [Deno](https://deno.com) instalado para descargar de YouTube.
