-- =============================================================
-- Agente de Reseñas — esquema v1
-- Multi-tenant: cada Business pertenece a un usuario (owner_user_id).
-- RLS activado en todas las tablas; el worker usa la service role key.
-- =============================================================

create extension if not exists "pgcrypto";

-- ---------- Negocios (tenant) ----------
create table public.businesses (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  sector text,
  -- BrandVoice: { tono, valores[], frases_prohibidas[], frases_firma[], idiomas[] }
  brand_voice jsonb not null default '{}'::jsonb,
  -- AutoPublishPolicy.mode — riesgo alto SIEMPRE va a humano (regla en código, no configurable)
  auto_publish_policy text not null default 'auto_positive_only'
    check (auto_publish_policy in ('always_approve', 'auto_positive_only', 'full_auto')),
  stripe_customer_id text,
  subscription_status text not null default 'inactive',
  created_at timestamptz not null default now()
);

-- ---------- Reseñas (capa de lectura, agnóstica de fuente) ----------
create table public.reviews (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references public.businesses (id) on delete cascade,
  source text not null default 'manual',
  -- ID externo (Google/Yelp/...) o hash del contenido para entrada manual.
  -- Garantiza idempotencia: la misma reseña no se procesa dos veces.
  external_id text not null,
  author text,
  rating int check (rating between 1 and 5),
  text text not null,
  review_created_at timestamptz,
  raw_payload jsonb,
  created_at timestamptz not null default now(),
  unique (business_id, source, external_id)
);

-- ---------- Clasificación (salida de Fable 5) ----------
create table public.classifications (
  id uuid primary key default gen_random_uuid(),
  review_id uuid not null unique references public.reviews (id) on delete cascade,
  sentiment text not null check (sentiment in ('positivo', 'neutral', 'negativo')),
  risk_level text not null check (risk_level in ('bajo', 'medio', 'alto')),
  topics text[] not null default '{}',
  escalation_note text,
  model_version text not null,
  created_at timestamptz not null default now()
);

-- ---------- Borradores de respuesta ----------
create table public.drafts (
  id uuid primary key default gen_random_uuid(),
  review_id uuid not null references public.reviews (id) on delete cascade,
  text text not null,
  status text not null default 'draft'
    check (status in ('draft', 'requires_human', 'approved', 'published', 'rejected')),
  model_version text not null,
  created_by text not null default 'agent',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index drafts_review_id_idx on public.drafts (review_id);
create index drafts_status_idx on public.drafts (status);

-- ---------- Audit log (toda escritura queda registrada) ----------
create table public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references public.businesses (id) on delete cascade,
  entity text not null,
  entity_id uuid,
  action text not null,
  actor text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index audit_logs_business_idx on public.audit_logs (business_id, created_at desc);

-- ---------- Cola de trabajos (procesamiento async) ----------
create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references public.businesses (id) on delete cascade,
  type text not null default 'process_review',
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending'
    check (status in ('pending', 'processing', 'done', 'error')),
  attempts int not null default 0,
  last_error text,
  run_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index jobs_pending_idx on public.jobs (status, run_at);

-- Reclamo atómico de trabajos para el worker (evita doble procesamiento)
create or replace function public.claim_jobs(batch_size int default 5)
returns setof public.jobs
language sql
security definer
as $$
  update public.jobs
  set status = 'processing', attempts = attempts + 1
  where id in (
    select id from public.jobs
    where status = 'pending' and run_at <= now()
    order by created_at
    limit batch_size
    for update skip locked
  )
  returning *;
$$;

-- =============================================================
-- RLS: el dueño del negocio ve solo sus datos.
-- El worker y los webhooks usan la service role key (salta RLS).
-- =============================================================
alter table public.businesses enable row level security;
alter table public.reviews enable row level security;
alter table public.classifications enable row level security;
alter table public.drafts enable row level security;
alter table public.audit_logs enable row level security;
alter table public.jobs enable row level security;

create policy "owner full access" on public.businesses
  for all using (owner_user_id = auth.uid()) with check (owner_user_id = auth.uid());

create policy "owner reviews" on public.reviews
  for all using (business_id in (select id from public.businesses where owner_user_id = auth.uid()))
  with check (business_id in (select id from public.businesses where owner_user_id = auth.uid()));

create policy "owner classifications" on public.classifications
  for select using (review_id in (
    select r.id from public.reviews r
    join public.businesses b on b.id = r.business_id
    where b.owner_user_id = auth.uid()
  ));

create policy "owner drafts read" on public.drafts
  for select using (review_id in (
    select r.id from public.reviews r
    join public.businesses b on b.id = r.business_id
    where b.owner_user_id = auth.uid()
  ));

-- El dueño puede editar/aprobar/rechazar/publicar borradores de sus reseñas.
-- La creación de borradores queda reservada al worker (service role).
create policy "owner drafts update" on public.drafts
  for update using (review_id in (
    select r.id from public.reviews r
    join public.businesses b on b.id = r.business_id
    where b.owner_user_id = auth.uid()
  ));

create policy "owner audit read" on public.audit_logs
  for select using (business_id in (select id from public.businesses where owner_user_id = auth.uid()));

create policy "owner audit insert" on public.audit_logs
  for insert with check (business_id in (select id from public.businesses where owner_user_id = auth.uid()));

create policy "owner jobs read" on public.jobs
  for select using (business_id in (select id from public.businesses where owner_user_id = auth.uid()));

create policy "owner jobs insert" on public.jobs
  for insert with check (business_id in (select id from public.businesses where owner_user_id = auth.uid()));
