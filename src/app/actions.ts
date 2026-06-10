"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ingestManual } from "@/lib/ingest";
import { logAudit } from "@/lib/audit";
import type { AutoPublishMode, BrandVoice } from "@/lib/types";

async function requireUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return { supabase, user };
}

// ---------- Negocios ----------

export async function createBusiness(formData: FormData) {
  const { supabase, user } = await requireUser();
  const name = String(formData.get("name") ?? "").trim();
  const sector = String(formData.get("sector") ?? "").trim() || null;
  if (!name) return;

  const { data, error } = await supabase
    .from("businesses")
    .insert({ owner_user_id: user.id, name, sector })
    .select("id")
    .single();
  if (error) throw new Error(error.message);

  await logAudit(supabase, {
    business_id: data.id,
    entity: "business",
    entity_id: data.id,
    action: "create",
    actor: `user:${user.id}`,
  });

  redirect(`/b/${data.id}`);
}

export async function updateSettings(formData: FormData) {
  const { supabase, user } = await requireUser();
  const businessId = String(formData.get("business_id"));

  const brandVoice: BrandVoice = {
    tono: String(formData.get("tono") ?? "").trim() || undefined,
    valores: splitList(formData.get("valores")),
    frases_prohibidas: splitList(formData.get("frases_prohibidas")),
    frases_firma: splitList(formData.get("frases_firma")),
    idiomas: splitList(formData.get("idiomas")),
  };

  const policy = String(formData.get("auto_publish_policy")) as AutoPublishMode;
  const validPolicies: AutoPublishMode[] = ["always_approve", "auto_positive_only", "full_auto"];

  const { error } = await supabase
    .from("businesses")
    .update({
      name: String(formData.get("name") ?? "").trim() || undefined,
      sector: String(formData.get("sector") ?? "").trim() || null,
      brand_voice: brandVoice,
      auto_publish_policy: validPolicies.includes(policy) ? policy : "auto_positive_only",
    })
    .eq("id", businessId);
  if (error) throw new Error(error.message);

  await logAudit(supabase, {
    business_id: businessId,
    entity: "business",
    entity_id: businessId,
    action: "update_settings",
    actor: `user:${user.id}`,
    metadata: { auto_publish_policy: policy },
  });

  revalidatePath(`/b/${businessId}/settings`);
}

function splitList(value: FormDataEntryValue | null): string[] | undefined {
  const items = String(value ?? "")
    .split(/[\n;]/)
    .map((s) => s.trim())
    .filter(Boolean);
  return items.length ? items : undefined;
}

// ---------- Ingesta ----------

export async function ingestReviews(formData: FormData) {
  const { supabase, user } = await requireUser();
  const businessId = String(formData.get("business_id"));
  const kind = formData.get("kind") === "csv" ? "csv" : "paste";

  let content = String(formData.get("content") ?? "");
  const file = formData.get("file");
  if (file instanceof File && file.size > 0) {
    content = await file.text();
  }

  const { inserted, skipped } = await ingestManual(supabase, {
    businessId,
    input: { kind, content },
    actor: `user:${user.id}`,
  });

  revalidatePath(`/b/${businessId}`);
  redirect(`/b/${businessId}?ingested=${inserted}&skipped=${skipped}`);
}

// ---------- Borradores (aprobación humana) ----------

type DraftAction = "approve" | "reject" | "publish" | "save";

export async function updateDraft(formData: FormData) {
  const { supabase, user } = await requireUser();
  const draftId = String(formData.get("draft_id"));
  const businessId = String(formData.get("business_id"));
  const reviewId = String(formData.get("review_id"));
  const action = String(formData.get("action")) as DraftAction;
  const text = String(formData.get("text") ?? "").trim();

  const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (text) patch.text = text;

  switch (action) {
    case "approve":
      patch.status = "approved";
      break;
    case "reject":
      patch.status = "rejected";
      break;
    case "publish":
      // v1: "publicar" = marcar como publicada; el humano copia y pega la
      // respuesta en la plataforma. v1.1: updateReply vía adaptador Google.
      patch.status = "published";
      break;
    case "save":
      break;
    default:
      throw new Error(`Acción desconocida: ${action}`);
  }

  const { error } = await supabase.from("drafts").update(patch).eq("id", draftId);
  if (error) throw new Error(error.message);

  await logAudit(supabase, {
    business_id: businessId,
    entity: "draft",
    entity_id: draftId,
    action,
    actor: `user:${user.id}`,
    metadata: { review_id: reviewId, edited: Boolean(text) },
  });

  revalidatePath(`/b/${businessId}/review/${reviewId}`);
  revalidatePath(`/b/${businessId}`);
}
