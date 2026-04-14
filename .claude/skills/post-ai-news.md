---
name: post-ai-news
description: Busca noticias recientes de IA, las verifica con Claude y publica posts adaptados en LinkedIn y Threads en español
---

Ejecuta el agente de publicación de noticias de IA corriendo `python agent.py` desde el directorio del proyecto.

El agente:
1. Obtiene artículos de las últimas 48h de fuentes confiables (OpenAI, Anthropic, Google, TechCrunch, MIT, etc.)
2. Usa Claude para verificar la credibilidad del contenido y seleccionar el más relevante
3. Genera un post adaptado para LinkedIn (profesional-casual, ~1300 chars, con hashtags)
4. Genera un post adaptado para Threads (más corto, conversacional, ~500 chars)
5. Publica automáticamente en ambas plataformas
6. Guarda logs en `logs/agent.log`

Si hay errores de autenticación, verifica que el archivo `.env` contenga:
- `ANTHROPIC_API_KEY`
- `LINKEDIN_ACCESS_TOKEN` y `LINKEDIN_PERSON_ID`
- `THREADS_ACCESS_TOKEN` y `THREADS_USER_ID`

Para configurar el cron (2 veces al día a las 9:00 y 19:00):
```
crontab -e
# Añadir la línea:
0 9,19 * * * /home/user/outreach-bot/run.sh
```
