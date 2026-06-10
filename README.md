# Agente de Reseñas y Reputación (v1)

SaaS que ingiere reseñas de clientes, las clasifica por sentimiento y riesgo con
**Claude Fable 5**, redacta respuestas en la voz de marca del negocio y las enruta a
aprobación humana o auto-aprobación según la política de cada cliente.

## Stack elegido y por qué

| Capa | Elección | Por qué |
|---|---|---|
| Web + API | **Next.js 15 (App Router, TS)** | Un solo deploy para UI y API; server actions simplifican formularios; lo conoces. |
| Auth + DB | **Supabase (Postgres + RLS)** | Multi-tenant real con Row Level Security a nivel de base de datos (cada dueño solo ve sus negocios); auth lista; lo conoces. |
| Cola/worker | **Tabla `jobs` en Postgres + worker Node** | Para el volumen de v1 no se justifica Redis/BullMQ: una tabla con `FOR UPDATE SKIP LOCKED` (función `claim_jobs`) da reclamo atómico, reintentos con backoff y cero infraestructura extra. Si el volumen crece, se cambia el backend de cola sin tocar el dominio. |
| Billing | **Stripe Checkout + webhook** | Suscripción por negocio; estándar. |
| IA | **`claude-fable-5` vía SDK oficial** | Dos llamadas separadas: clasificación con salida JSON estricta (`output_config.format` + fallback fail-safe) y redacción creativa con la BrandVoice en el system prompt. `model_version` se guarda en cada output. |

**Principio central (no romper):** el core no depende de ninguna API externa de
reseñas. La ingesta es agnóstica de fuente (interfaz `ReviewSource`, v1 solo
`ManualSource`) y la capa de escritura/publicación está separada con guardrails,
auditoría e idempotencia.

## Cómo correr en local

### 1. Requisitos
- Node 20+
- Un proyecto Supabase ([supabase.com](https://supabase.com), gratis) o Supabase CLI local (`supabase start`)
- Clave de Anthropic
- (Opcional para billing) cuenta Stripe en modo test

### 2. Configurar
```bash
npm install
cp .env.example .env   # y rellena los valores
```

Aplica la migración en tu proyecto Supabase:
- **Dashboard:** SQL Editor → pega `supabase/migrations/0001_init.sql` → Run
- **CLI:** `supabase db push`

En Supabase → Authentication → Providers, asegúrate de tener **Email** habilitado.
Para desarrollo, desactiva "Confirm email" o usa el usuario demo del seed.

### 3. Seed (negocio de prueba + 10 reseñas)
```bash
npm run seed
```
Crea el usuario `demo@agente.local` / `demo123456`, el negocio **Café Luna** con su
BrandVoice, y encola 10 reseñas de ejemplo (positivas, neutras, negativas y una de
**riesgo alto** que siempre escala a humano).

### 4. Arrancar (dos procesos)
```bash
npm run dev      # web en http://localhost:3000
npm run worker   # procesa la cola: clasifica + redacta con Fable 5
```

Entra con el usuario demo, abre **Café Luna** y mira la cola de aprobación llenarse.

### 5. Stripe (opcional en dev)
```bash
stripe listen --forward-to localhost:3000/api/stripe/webhook
```
Copia el `whsec_...` a `STRIPE_WEBHOOK_SECRET`. Crea un producto/precio recurrente
en el dashboard de Stripe y pon su ID en `STRIPE_PRICE_ID`.

## Variables de entorno

Ver `.env.example`. Nunca se commitean secretos; `ANTHROPIC_API_KEY` solo vive en
el entorno del worker/servidor.

## Flujo end-to-end

```
Ingesta (pegar/CSV) → tabla reviews (idempotente por hash)
  → job en cola → worker:
      1. Clasificación (Fable 5, JSON estricto; parseo fallido ⇒ riesgo alto)
      2. Borrador (Fable 5, voz de marca en system prompt)
      3. Enrutamiento: riesgo alto ⇒ SIEMPRE requires_human (guardrail fijo);
         si no, según AutoPublishPolicy del negocio
  → UI: cola de aprobación (editar / aprobar / rechazar / copiar / marcar publicada)
  → audit_logs registra cada escritura (quién, qué, cuándo, con qué modelo)
```

### Guardrails implementados
1. Riesgo alto → siempre humano (en código, `src/lib/routing.ts`; no configurable).
2. Fallo de parseo de clasificación → tratado como riesgo alto (`src/lib/classify.ts`).
3. Separación lectura (ingesta) / escritura (aprobación-publicación).
4. Idempotencia: unique `(business_id, source, external_id)` + worker que no re-procesa.
5. Sin secretos en código (todo por env).
6. Audit log de toda escritura (`audit_logs`).
7. Reglas duras de redacción: nunca admitir culpa legal, nunca prometer compensación, nunca datos privados, siempre invitar a canal privado en negativas.

## Roadmap v1.1 — adaptador Google Business Profile

La interfaz ya existe (`src/lib/sources/types.ts`). Pasos:

1. **Acceso:** solicitar acceso a la Google Business Profile API (requiere GBP
   verificado con 60+ días, sitio web válido y aprobación manual de Google).
2. **OAuth 2.0** con `access_type=offline` para refresh tokens.
   Scope: `https://www.googleapis.com/auth/business.manage`.
3. **Lectura:** implementar `GoogleBusinessProfileSource implements ReviewSource`
   que liste reseñas y las normalice a `IncomingReview` (el `external_id` es el ID
   real de Google ⇒ la idempotencia ya funciona).
4. **Escritura:** en `updateDraft` acción `publish`, llamar `updateReply`:
   `PUT https://mybusiness.googleapis.com/v4/{name=accounts/*/locations/*/reviews/*}/reply`
   con body `ReviewReply`. **Verificar el endpoint contra la doc oficial aprobada
   antes de implementar** (la forma exacta varía por versión de API).
5. Yelp/Facebook/TripAdvisor: misma interfaz, mismo flujo.

## Visión de plataforma

El core (ingesta agnóstica → clasificación → enrutamiento con guardrails →
aprobación humana → auditoría) no sabe nada de "reseñas" más allá del prompt y la
fuente de datos. Los próximos agentes (leads, cobros, soporte WhatsApp) reusan las
mismas tablas/colas cambiando `source` y los prompts.

## Estructura

```
supabase/migrations/0001_init.sql   esquema + RLS + claim_jobs()
src/lib/                             dominio: classify, draft, routing, ingest, sources/
src/app/                             UI + server actions + rutas Stripe
scripts/worker.ts                    worker de cola (npm run worker)
scripts/seed.ts                      datos de prueba (npm run seed)
```
