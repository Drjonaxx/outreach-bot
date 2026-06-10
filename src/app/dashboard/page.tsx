import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { createBusiness } from "@/app/actions";
import type { Business } from "@/lib/types";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: businesses } = await supabase
    .from("businesses")
    .select("*")
    .order("created_at", { ascending: false })
    .returns<Business[]>();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold">Tus negocios</h1>
        <p className="text-sm text-stone-500">
          Cada negocio tiene su propia voz de marca, política de publicación y cola de reseñas.
        </p>
      </div>

      <ul className="grid gap-4 sm:grid-cols-2">
        {(businesses ?? []).map((b) => (
          <li key={b.id}>
            <Link
              href={`/b/${b.id}`}
              className="block rounded-xl border border-stone-200 bg-white p-5 shadow-sm hover:border-stone-400"
            >
              <div className="font-medium">{b.name}</div>
              <div className="mt-1 text-sm text-stone-500">{b.sector ?? "Sin sector"}</div>
              <div className="mt-2 text-xs text-stone-400">
                Política: {policyLabel(b.auto_publish_policy)} · Suscripción: {b.subscription_status}
              </div>
            </Link>
          </li>
        ))}
        {(businesses ?? []).length === 0 && (
          <li className="text-sm text-stone-500">Todavía no tienes negocios. Crea el primero abajo.</li>
        )}
      </ul>

      <form
        action={createBusiness}
        className="max-w-md space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm"
      >
        <h2 className="font-medium">Nuevo negocio</h2>
        <input
          name="name"
          required
          placeholder="Nombre (ej: Café Luna)"
          className="w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
        />
        <input
          name="sector"
          placeholder="Sector (ej: restaurante)"
          className="w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
        />
        <button className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700">
          Crear
        </button>
      </form>
    </div>
  );
}

function policyLabel(p: string) {
  switch (p) {
    case "full_auto": return "auto total";
    case "auto_positive_only": return "auto solo positivas";
    default: return "aprobar todo";
  }
}
