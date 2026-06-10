import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { RiskBadge, SentimentBadge, StatusBadge } from "@/components/badges";
import type { Business, Classification, Draft, Review } from "@/lib/types";

interface ReviewRow extends Review {
  classifications: Classification | null;
  drafts: Draft[];
}

export default async function BusinessPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ filter?: string; ingested?: string; skipped?: string }>;
}) {
  const { id } = await params;
  const { filter, ingested, skipped } = await searchParams;
  const supabase = await createClient();

  const { data: business } = await supabase
    .from("businesses")
    .select("*")
    .eq("id", id)
    .maybeSingle<Business>();
  if (!business) notFound();

  const { data: reviews } = await supabase
    .from("reviews")
    .select("*, classifications(*), drafts(*)")
    .eq("business_id", id)
    .order("created_at", { ascending: false })
    .returns<ReviewRow[]>();

  const rows = (reviews ?? []).map((r) => ({
    ...r,
    classification: Array.isArray(r.classifications) ? r.classifications[0] ?? null : r.classifications,
    activeDraft: pickActiveDraft(r.drafts ?? []),
  }));

  const pending = rows.filter((r) => r.activeDraft?.status === "requires_human");
  const visible =
    filter === "pendientes" ? pending : rows;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{business.name}</h1>
          <p className="text-sm text-stone-500">
            {rows.length} reseñas · {pending.length} esperando aprobación humana
          </p>
        </div>
        <div className="flex gap-2 text-sm">
          <Link href={`/b/${id}/ingest`} className="rounded-md bg-stone-900 px-3 py-2 font-medium text-white hover:bg-stone-700">
            + Ingestar reseñas
          </Link>
          <Link href={`/b/${id}/settings`} className="rounded-md border border-stone-300 bg-white px-3 py-2 hover:border-stone-500">
            Ajustes
          </Link>
        </div>
      </div>

      {ingested !== undefined && (
        <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Ingesta completada: {ingested} nuevas, {skipped ?? 0} duplicadas omitidas. El worker las
          procesará en segundos (asegúrate de tener <code>npm run worker</code> corriendo).
        </p>
      )}

      <div className="flex gap-2 text-sm">
        <Link
          href={`/b/${id}`}
          className={`rounded-full px-3 py-1 ${!filter ? "bg-stone-900 text-white" : "bg-white border border-stone-300"}`}
        >
          Todas
        </Link>
        <Link
          href={`/b/${id}?filter=pendientes`}
          className={`rounded-full px-3 py-1 ${filter === "pendientes" ? "bg-stone-900 text-white" : "bg-white border border-stone-300"}`}
        >
          Cola de aprobación ({pending.length})
        </Link>
      </div>

      <ul className="space-y-3">
        {visible.map((r) => (
          <li key={r.id}>
            <Link
              href={`/b/${id}/review/${r.id}`}
              className="block rounded-xl border border-stone-200 bg-white p-4 shadow-sm hover:border-stone-400"
            >
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {r.rating && <span className="font-medium text-amber-600">{"★".repeat(r.rating)}</span>}
                <span className="text-stone-500">{r.author ?? "Anónimo"}</span>
                {r.classification && (
                  <>
                    <SentimentBadge value={r.classification.sentiment} />
                    <RiskBadge value={r.classification.risk_level} />
                  </>
                )}
                {r.activeDraft ? (
                  <StatusBadge value={r.activeDraft.status} />
                ) : (
                  <span className="rounded-full bg-stone-100 px-2 py-0.5 text-stone-500">procesando…</span>
                )}
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-stone-700">{r.text}</p>
            </Link>
          </li>
        ))}
        {visible.length === 0 && (
          <li className="text-sm text-stone-500">
            {filter === "pendientes" ? "Nada esperando aprobación. 🎉" : "Sin reseñas todavía."}
          </li>
        )}
      </ul>
    </div>
  );
}

function pickActiveDraft(drafts: Draft[]): Draft | null {
  const active = drafts.filter((d) => d.status !== "rejected");
  const pool = active.length ? active : drafts;
  return pool.sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null;
}
