# beingvortex — Agente de Noticias de IA para Threads

Bot automático que busca noticias verificadas de inteligencia artificial,
escribe posts bilingües (español + inglés) y los publica en Threads.

Tono: **educativo y directo**. Solo hechos confirmados — nunca rumores ni noticias falsas.

---

## Cómo funciona

```
Cada N horas:
  1. Claude busca noticias de IA de las últimas 48h (web search)
  2. Verifica cada noticia en múltiples fuentes
  3. Escribe 2 posts por noticia (ES + EN, máx 480 caracteres)
  4. Publica en Threads
  5. Registra lo publicado para no repetir
```

---

## Instalación

```bash
pip install -r requirements.txt
cp .env.example .env     # luego edita .env con tus credenciales
```

---

## Configuración (.env)

| Variable | Qué es | Dónde conseguirlo |
|----------|--------|-------------------|
| `ANTHROPIC_API_KEY` | Key de Claude | console.anthropic.com |
| `THREADS_ACCESS_TOKEN` | Token de 60 días | developers.facebook.com (ver abajo) |
| `THREADS_USER_ID` | Tu ID de Threads | endpoint `/me` (ver abajo) |
| `MAX_POSTS_PER_RUN` | Noticias por run (default 2) | — |
| `SCHEDULE_HOURS` | Horas entre runs (default 4) | — |
| `MAX_NEWS_ITEMS` | Noticias a buscar por run (default 5) | — |

### Conseguir las credenciales de Threads

1. Entra a **developers.facebook.com** → "Empezar" → regístrate como desarrollador
2. "Crear aplicación" → tipo "Other" / "Consumer"
3. "Add Product" → **Threads API** → Set Up
4. Agrega los permisos `threads_basic` y `threads_content_publish`
5. Genera un User Token, luego conviértelo a uno de 60 días:
   ```bash
   curl "https://graph.threads.net/access_token?grant_type=th_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&access_token=TOKEN_CORTO"
   ```
6. Obtén tu User ID:
   ```bash
   curl "https://graph.threads.net/v1.0/me?access_token=TOKEN_LARGO"
   ```

---

## Uso

```bash
python agent.py --dry-run        # Genera y muestra posts SIN publicar (los guarda en posts_YYYY-MM-DD.md)
python agent.py --check-auth     # Verifica que el token de Threads funciona
python agent.py --once           # Busca y publica una vez
python agent.py --schedule       # Modo automático (cada SCHEDULE_HOURS horas)
python agent.py --refresh-token  # Renueva el token de Threads (cada ~50 días)
```

Sin argumentos, corre en `--dry-run` por seguridad.

### Correr 24/7

**Cron** (cada 4 horas):
```bash
0 */4 * * * cd /ruta/outreach-bot && python agent.py --once >> agent.log 2>&1
```

**Proceso continuo:**
```bash
python agent.py --schedule
```

---

## Estructura

```
outreach-bot/
├── agent.py                  # Orquestador y CLI
├── core/
│   ├── news_finder.py        # Busca y verifica noticias (Claude + web_search)
│   ├── post_writer.py        # Genera posts ES/EN
│   ├── threads_client.py     # Publica en Threads API
│   └── tracker.py            # Deduplicación
├── requirements.txt
└── .env.example
```

---

## Modo manual (sin Threads API)

Si no quieres configurar la Threads API, usa `--dry-run`: el agente genera los
posts y los guarda en `posts_YYYY-MM-DD.md`. Solo copias y pegas en Threads.
