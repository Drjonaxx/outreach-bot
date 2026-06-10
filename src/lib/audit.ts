import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * Registra toda escritura relevante (PLAN §4.6/§9).
 * Se llama con el cliente que corresponda (usuario o service role).
 */
export async function logAudit(
  db: SupabaseClient,
  entry: {
    business_id: string;
    entity: string;
    entity_id?: string | null;
    action: string;
    actor: string; // "agent:claude-fable-5" | "user:<id>" | "system:stripe"
    metadata?: Record<string, unknown>;
  }
): Promise<void> {
  const { error } = await db.from("audit_logs").insert({
    business_id: entry.business_id,
    entity: entry.entity,
    entity_id: entry.entity_id ?? null,
    action: entry.action,
    actor: entry.actor,
    metadata: entry.metadata ?? {},
  });
  if (error) console.error("audit_logs insert failed:", error.message);
}
