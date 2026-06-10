import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { updateDraft } from "@/app/actions";
import { CopyButton } from "@/components/copy-button";
import { RiskBadge, SentimentBadge, StatusBadge } from "@/components/badges";
import type { Classification, Draft, Review } from "@/lib/types";

export default async function ReviewDetailPage({
  params,
}: {
  params: Promise<{ id: string; reviewId: string }>;
}) {
  const { id, reviewId } = await params;
  const supabase = await createClient();

  const { data: review } = await supabase
    .from("reviews")
    .select("*")
    .eq("id", reviewId)
    .maybeSingle<Review>();
  if (!review || review.business_id !== id) notFound();

  const { data: classification } = await supabase
    .from("classifications")
    .select("*")
    .eq("review_id", reviewId)
    .maybeSingle<Classification>();

  const { data: drafts } = await supabase
    .from("drafts")
    .select("*")
    .eq("review_id", reviewId)
    .order("created_at", { ascending: false })
    .returns<Draft[]>();

  const draft = (drafts ?? []).find((d) => d.status !== "rejected") ?? (drafts ?? [])[0] ?? null;

  return (
    <div className="space-y-6">
      <Link href={`/b/${id}`} className="text-sm text-stone-500 hover:text-stone-900">
        ← Volver a reseñas
      </Link>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {review.rating && <span className="text-amber-600">{"★".repeat(review.rating)}</span>}
          <span className="font-medium">{review.author ?? "Anónimo"}</span>
          <span className="text-xs text-stone-400">fuente: {review.source}</span>
        </div>
        <p className="mt-3 whitespace-pre-wrap text-stone-800">{review.text}</p>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-stone-500">Clasificación</h2>
        {classification ? (
          <div className="mt-2 space-y-2">
            <div className="flex flex-wrap gap-2 text-xs">
              <SentimentBadge value={classification.sentiment} />
              <RiskBadge value={classification.risk_level} />
              {classification.topics.map((t) => (
                <span key={t} className="rounded-full bg-stone-100 px-2 py-0.5 text-stone-600">
                  {t}
                </span>
              ))}
            </div>
            {classification.escalation_note && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
                ⚠️ Escalada a humano: {classification.escalation_note}
              </p>
            )}
            <p className="text-xs text-stone-400">modelo: {classification.model_version}</p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-stone-500">
            Pendiente de procesar. ¿Está corriendo el worker? (<code>npm run worker</code>)
          </p>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-stone-500">Respuesta propuesta</h2>
          {draft && <StatusBadge value={draft.status} />}
        </div>

        {draft ? (
          <form action={updateDraft} className="mt-3 space-y-3">
            <input type="hidden" name="draft_id" value={draft.id} />
            <input type="hidden" name="business_id" value={id} />
            <input type="hidden" name="review_id" value={reviewId} />
            <textarea
              name="text"
              defaultValue={draft.text}
              rows={6}
              className="w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
            />
            <div className="flex flex-wrap gap-2">
              {(draft.status === "requires_human" || draft.status === "draft") && (
                <>
                  <button
                    name="action"
                    value="approve"
                    className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-500"
                  >
                    Aprobar
                  </button>
                  <button
                    name="action"
                    value="reject"
                    className="rounded-md bg-stone-200 px-3 py-2 text-sm hover:bg-stone-300"
                  >
                    Rechazar
                  </button>
                </>
              )}
              {draft.status === "approved" && (
                <button
                  name="action"
                  value="publish"
                  className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500"
                >
                  Marcar como publicada
                </button>
              )}
              <button
                name="action"
                value="save"
                className="rounded-md border border-stone-300 px-3 py-2 text-sm hover:border-stone-500"
              >
                Guardar edición
              </button>
              <CopyButton text={draft.text} />
            </div>
            <p className="text-xs text-stone-400">
              modelo: {draft.model_version} · creado por: {draft.created_by}
            </p>
            {(draft.status === "approved" || draft.status === "published") && (
              <p className="rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-800">
                v1: copia la respuesta y pégala en Google/Yelp/Facebook. En v1.1 el adaptador de
                Google publicará automáticamente vía API.
              </p>
            )}
          </form>
        ) : (
          <p className="mt-2 text-sm text-stone-500">Aún no hay borrador para esta reseña.</p>
        )}
      </section>
    </div>
  );
}
