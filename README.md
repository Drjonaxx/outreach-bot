# outreach-bot

Este repo junta varios proyectos, cada uno en su propia rama. `main` es el
índice: dice qué hay en cada rama, qué corre solo y qué quedó en pausa.

## Lo que está vivo

| Rama | Qué es | Qué corre solo |
|------|--------|----------------|
| `claude/clipper` | **¿Qué Dijo El Gringo?** Clips verticales con subtítulos de streamers para YouTube Shorts, Instagram Reels y TikTok. | Cuatro tareas programadas de Claude: clips diarios (8:47 am), subida de madrugada a YouTube (3 y 4 am), publicación al mediodía (11:53 am) y en la noche (7:56 pm). TikTok es manual. El render corre en `clipper.yml` con cada push del trabajo. |
| `claude/clipper-out` | Resultados del clipper (transcripciones y clips). | La escribe `clipper.yml`. No se toca a mano. |
| `claude/kit-ventas-clara` | Kit para vender **Clara**: 39 clínicas de Puerto Rico, guion de entrevistas, oferta y plantillas. | Nada: las entrevistas son en persona. |

En `main`, `.github/workflows/clipper-pruebas.yml` corre todos los días las
pruebas del clipper sobre lo último de `claude/clipper`, sin tocar esa rama.

## Prototipos en pausa

Funcionan como punto de partida pero nadie los usa. Antes de retomar uno,
mira si otra cosa ya lo cubre.

| Rama | Qué es | Estado |
|------|--------|--------|
| `claude/beingvortex-news-agent-RSciw` | Agente que busca noticias de IA y publica en Threads (@beingvortex). | Sin desplegar. En Make existe «Post Threads IA Diario (a email)», que manda el post listo a tu correo cada mañana: está **apagado**, se prende en Make con un toque. |
| `claude/make-tools-exploration-Cd7V2` | **Análisis IA Diario**, PWA en Netlify que pide el análisis a un escenario de Make. | En línea; el escenario de Make está activo. |
| `claude/busy-dijkstra-8c2s34` | **Agente de Reseñas**: SaaS que clasifica reseñas y redacta respuestas con aprobación humana, con Stripe. | v1 completa, sin clientes ni despliegue. |
| `claude/audit-instabiz-workflow-fM2CM` | **InstaBiz Sites**: generador de sitios para negocios locales (Next.js + Prisma). | Sin desplegar. |
| `claude/global-info-collection-system-q2Vi2` | Analizador de audiencia (Google Trends, Reddit, HackerNews, YouTube). | Script local. |
| `claude/review-chat-errors-OTMcI` | Bot de ideas de contenido con Google Trends, HackerNews, YouTube y NewsAPI, con web app. | Script local. |
| `claude/brainstorm-project-ideas-rMiO0` | Cold emails personalizados con Claude que quedan como borradores en Gmail. | Reemplazado por los correos a prospectos del buscador (`buscador-propiedades`). |
| `claude/outreach-bot-generator-sSVZd` | DMs de Instagram y correos en español para negocios locales. | Reemplazado por lo mismo. |
| `claude/create-demo-generator-vgrXo` | Genera una demo HTML para un negocio local. | Reemplazado por la demo del buscador. |
| `claude/create-new-skill-JMpLh` | Bot de noticias de IA para LinkedIn y Threads. | Reemplazado por `beingvortex-news-agent`. |
| `claude/install-firecrawl-nNWBn`, `claude/install-n8n-mcp-lsBoY` | Configuración suelta (Firecrawl, MCP de n8n). | Solo configuración. |

## Dónde está lo demás

| Repo | Qué es |
|------|--------|
| `Clara` | Coordinadora con IA para med spas (WhatsApp, citas, formulario de salud). |
| `buscador-propiedades` | Buscador con marca propia para corredores y dealers en Puerto Rico, con 379 prospectos. |
| `btc-dca-bot` | DCA semanal de BTC, asistente por Siri, El Lobo (acciones) y Vigía (monitoreo de sitios). |
| `VENTAS` | Mesa de intermediación para finder's fees. |
