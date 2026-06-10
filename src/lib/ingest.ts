import type { SupabaseClient } from "@supabase/supabase-js";
import { ManualSource, type ManualInput } from "./sources/manual";
import { logAudit } from "./audit";

/**
 * Ingesta de reseñas (capa de lectura) + encolado del procesamiento async.
 * Idempotente: reseñas duplicadas (mismo business/source/external_id) se ignoran
 * y no generan trabajos nuevos.
 */
export async function ingestManual(
  db: SupabaseClient,
  params: { businessId: string; input: ManualInput; actor: string }
): Promise<{ inserted: number; skipped: number }> {
  const source = new ManualSource();
  const incoming = await source.fetchReviews(params.input);
  if (incoming.length === 0) return { inserted: 0, skipped: 0 };

  let inserted = 0;
  let skipped = 0;

  for (const r of incoming) {
    const { data, error } = await db
      .from("reviews")
      .upsert(
        {
          business_id: params.businessId,
          source: source.name,
          external_id: r.external_id,
          author: r.author,
          rating: r.rating,
          text: r.text,
          review_created_at: r.review_created_at,
          raw_payload: r.raw_payload ?? null,
        },
        { onConflict: "business_id,source,external_id", ignoreDuplicates: true }
      )
      .select("id")
      .maybeSingle();

    if (error) throw new Error(`Error insertando reseña: ${error.message}`);
    if (!data) {
      skipped++;
      continue;
    }

    inserted++;
    const { error: jobError } = await db.from("jobs").insert({
      business_id: params.businessId,
      type: "process_review",
      payload: { review_id: data.id },
    });
    if (jobError) throw new Error(`Error encolando trabajo: ${jobError.message}`);
  }

  await logAudit(db, {
    business_id: params.businessId,
    entity: "review",
    action: "ingest",
    actor: params.actor,
    metadata: { source: source.name, inserted, skipped },
  });

  return { inserted, skipped };
}
