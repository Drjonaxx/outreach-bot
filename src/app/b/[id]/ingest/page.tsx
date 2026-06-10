import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ingestReviews } from "@/app/actions";
import type { Business } from "@/lib/types";

export default async function IngestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: business } = await supabase
    .from("businesses")
    .select("id, name")
    .eq("id", id)
    .maybeSingle<Pick<Business, "id" | "name">>();
  if (!business) notFound();

  return (
    <div className="max-w-2xl space-y-6">
      <Link href={`/b/${id}`} className="text-sm text-stone-500 hover:text-stone-900">
        ← Volver a reseñas
      </Link>
      <h1 className="text-xl font-semibold">Ingestar reseñas — {business.name}</h1>
      <p className="text-sm text-stone-500">
        v1: entrada manual. En v1.1 conectaremos Google Business Profile como adaptador, sin tocar
        este flujo.
      </p>

      <form action={ingestReviews} className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <input type="hidden" name="business_id" value={id} />
        <input type="hidden" name="kind" value="paste" />
        <h2 className="font-medium">Pegar texto</h2>
        <p className="text-xs text-stone-500">Una reseña por línea, o bloques separados por línea en blanco.</p>
        <textarea
          name="content"
          rows={8}
          placeholder={"El servicio fue excelente, volveré seguro.\n\nTardaron 40 minutos en atenderme, muy mal."}
          className="w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
        />
        <button className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700">
          Ingestar
        </button>
      </form>

      <form action={ingestReviews} className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <input type="hidden" name="business_id" value={id} />
        <input type="hidden" name="kind" value="csv" />
        <h2 className="font-medium">Subir CSV</h2>
        <p className="text-xs text-stone-500">
          Cabeceras: <code>author,rating,text,date</code> — solo <code>text</code> es obligatoria.
        </p>
        <input type="file" name="file" accept=".csv,text/csv" className="block text-sm" />
        <button className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700">
          Subir e ingestar
        </button>
      </form>
    </div>
  );
}
