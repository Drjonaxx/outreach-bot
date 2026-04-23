# Audience Analyzer

Analiza tendencias y preferencias de audiencia sobre cualquier tema usando datos públicos de:

- **Google Trends** — que busca la gente, temas en alza, consultas relacionadas
- **Reddit** — que discuten, que les gusta, horarios de actividad
- **HackerNews** — temas populares en tecnología y negocios
- **YouTube** — videos con mas vistas, tags, canales dominantes
- **NewsAPI** — cobertura de medios, días más activos

## Instalacion

```bash
pip install -r requirements.txt
```

## Configuracion de APIs

Copia `.env.example` a `.env` y completa las claves:

```bash
cp .env.example .env
```

| API | Costo | Link |
|-----|-------|------|
| Google Trends | Gratis (sin clave) | — |
| HackerNews | Gratis (sin clave) | — |
| Reddit | Gratis | https://www.reddit.com/prefs/apps |
| YouTube | Gratis (10k req/dia) | https://console.cloud.google.com |
| NewsAPI | Gratis (100 req/dia) | https://newsapi.org |

## Uso

```bash
python main.py "moda sustentable"
python main.py "recetas veganas" --geo MX
python main.py "gaming" --timeframe "today 12-m"
```

### Opciones

| Opcion | Descripcion | Default |
|--------|-------------|---------|
| `keyword` | Tema a analizar | (requerido) |
| `--geo` | Pais para Google Trends (MX, US, AR...) | Mundial |
| `--timeframe` | Periodo de analisis | `today 3-m` |

## Que hace con los datos

El sistema produce un reporte con:
- Nivel de interes y si la tendencia sube o baja
- Subtemas y busquedas relacionadas en alza
- Posts mas populares de Reddit y hora pico de actividad
- Videos de YouTube con mas vistas y sus tags
- Cobertura en medios de comunicacion
- Recomendaciones de contenido accionables
