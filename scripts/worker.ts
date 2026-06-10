/**
 * Worker de procesamiento async (PLAN §7).
 *
 * Cola respaldada en Postgres (tabla jobs) con reclamo atómico vía claim_jobs()
 * (FOR UPDATE SKIP LOCKED) — varios workers pueden correr en paralelo sin
 * procesar dos veces el mismo trabajo.
 *
 * Uso: npm run worker
 */
import "dotenv/config";
import { createAdminClient } from "../src/lib/supabase/admin";
import { classifyReview } from "../src/lib/classify";
import { draftReply } from "../src/lib/draft";
import { decideDraftStatus } from "../src/lib/routing";
import { logAudit } from "../src/lib/audit";
import { MODEL_VERSION } from "../src/lib/anthropic";
import type { Business, Review } from "../src/lib/types";

const POLL_MS = parseInt(process.env.WORKER_POLL_INTERVAL_MS ?? "3000", 10);
const MAX_ATTEMPTS = 3;

const db = createAdminClient();

interface Job {
  id: string;
  business_id: string;
  type: string;
  payload: { review_id?: string };
  attempts: number;
}

async function main() {
  console.log(`[worker] arrancando — poll cada ${POLL_MS}ms, modelo ${MODEL_VERSION}`);
  for (;;) {
    try {
      const { data: jobs, error } = await db.rpc("claim_jobs", { batch_size: 5 });
      if (error) throw new Error(error.message);

      if (!jobs || jobs.length === 0) {
        await sleep(POLL_MS);
        continue;
      }

      for (const job of jobs as Job[]) {
        await handleJob(job);
      }
    } catch (err) {
      console.error("[worker] error en el loop:", err);
      await sleep(POLL_MS);
    }
  }
}

async function handleJob(job: Job) {
  console.log(`[worker] job ${job.id} (${job.type}) intento ${job.attempts}`);
  try {
    if (job.type === "process_review") {
      await processReview(job);
    } else {
      throw new Error(`Tipo de trabajo desconocido: ${job.type}`);
    }
    await db.from("jobs").update({ status: "done", last_error: null }).eq("id", job.id);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`[worker] job ${job.id} falló:`, message);
    const exhausted = job.attempts >= MAX_ATTEMPTS;
    await db
      .from("jobs")
      .update({
        status: exhausted ? "error" : "pending",
        last_error: message,
        // backoff exponencial simple
        run_at: new Date(Date.now() + 2 ** job.attempts * 5000).toISOString(),
      })
      .eq("id", job.id);
  }
}

async function processReview(job: Job) {
  const reviewId = job.payload.review_id;
  if (!reviewId) throw new Error("payload sin review_id");

  const { data: review, error: rErr } = await db
    .from("reviews")
    .select("*")
    .eq("id", reviewId)
    .single<Review>();
  if (rErr || !review) throw new Error(`Reseña ${reviewId} no encontrada`);

  const { data: business, error: bErr } = await db
    .from("businesses")
    .select("*")
    .eq("id", review.business_id)
    .single<Business>();
  if (bErr || !business) throw new Error(`Negocio ${review.business_id} no encontrado`);

  // --- 1. Clasificación (idempotente: si ya existe, se reutiliza) ---
  let classification = (
    await db.from("classifications").select("*").eq("review_id", reviewId).maybeSingle()
  ).data;

  if (!classification) {
    const { result, modelVersion } = await classifyReview(review);
    const { data, error } = await db
      .from("classifications")
      .insert({
        review_id: reviewId,
        sentiment: result.sentiment,
        risk_level: result.risk_level,
        topics: result.topics,
        escalation_note: result.escalation_note,
        model_version: modelVersion,
      })
      .select("*")
      .single();
    if (error) throw new Error(`Error guardando clasificación: ${error.message}`);
    classification = data;

    await logAudit(db, {
      business_id: business.id,
      entity: "classification",
      entity_id: data.id,
      action: "create",
      actor: `agent:${modelVersion}`,
      metadata: { review_id: reviewId, sentiment: result.sentiment, risk_level: result.risk_level },
    });
  }

  // --- 2. Borrador (idempotente: si ya hay un borrador activo, no duplicar) ---
  const { data: existingDrafts } = await db
    .from("drafts")
    .select("id, status")
    .eq("review_id", reviewId)
    .neq("status", "rejected");
  if (existingDrafts && existingDrafts.length > 0) {
    console.log(`[worker] reseña ${reviewId} ya tiene borrador activo; omitiendo`);
    return;
  }

  const classResult = {
    sentiment: classification.sentiment,
    risk_level: classification.risk_level,
    topics: classification.topics ?? [],
    escalation_note: classification.escalation_note,
  };

  const { text, modelVersion } = await draftReply({
    review,
    classification: classResult,
    businessName: business.name,
    sector: business.sector,
    brandVoice: business.brand_voice ?? {},
  });

  // --- 3. Enrutamiento con guardrail (riesgo alto → siempre humano) ---
  const status = decideDraftStatus(classResult, business.auto_publish_policy);

  const { data: draft, error: dErr } = await db
    .from("drafts")
    .insert({
      review_id: reviewId,
      text,
      status,
      model_version: modelVersion,
      created_by: "agent",
    })
    .select("id")
    .single();
  if (dErr) throw new Error(`Error guardando borrador: ${dErr.message}`);

  await logAudit(db, {
    business_id: business.id,
    entity: "draft",
    entity_id: draft.id,
    action: status === "approved" ? "auto_approve" : "create_requires_human",
    actor: `agent:${modelVersion}`,
    metadata: {
      review_id: reviewId,
      policy: business.auto_publish_policy,
      risk_level: classResult.risk_level,
      sentiment: classResult.sentiment,
    },
  });

  console.log(`[worker] reseña ${reviewId} procesada → draft ${draft.id} (${status})`);
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

main().catch((err) => {
  console.error("[worker] error fatal:", err);
  process.exit(1);
});
