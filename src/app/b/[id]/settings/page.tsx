import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { updateSettings } from "@/app/actions";
import type { Business } from "@/lib/types";

export default async function SettingsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: business } = await supabase
    .from("businesses")
    .select("*")
    .eq("id", id)
    .maybeSingle<Business>();
  if (!business) notFound();

  const voice = business.brand_voice ?? {};

  return (
    <div className="max-w-2xl space-y-6">
      <Link href={`/b/${id}`} className="text-sm text-stone-500 hover:text-stone-900">
        ← Volver a reseñas
      </Link>
      <h1 className="text-xl font-semibold">Ajustes — {business.name}</h1>

      <form action={updateSettings} className="space-y-6">
        <input type="hidden" name="business_id" value={id} />

        <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="font-medium">Negocio</h2>
          <label className="block text-sm">
            Nombre
            <input name="name" defaultValue={business.name} className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm" />
          </label>
          <label className="block text-sm">
            Sector
            <input name="sector" defaultValue={business.sector ?? ""} className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm" />
          </label>
        </section>

        <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="font-medium">Voz de marca</h2>
          <p className="text-xs text-stone-500">Se inyecta en el prompt de redacción. Listas separadas por punto y coma o saltos de línea.</p>
          <label className="block text-sm">
            Tono
            <input name="tono" defaultValue={voice.tono ?? ""} placeholder="cercano, cálido, profesional…" className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm" />
          </label>
          <label className="block text-sm">
            Valores
            <textarea name="valores" defaultValue={(voice.valores ?? []).join("\n")} rows={2} className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm" />
          </label>
          <label className="block text-sm">
            Frases firma
            <textarea name="frases_firma" defaultValue={(voice.frases_firma ?? []).join("\n")} rows={2} placeholder="¡Te esperamos pronto!" className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm" />
          </label>
          <label className="block text-sm">
            Frases prohibidas
            <textarea name="frases_prohibidas" defaultValue={(voice.frases_prohibidas ?? []).join("\n")} rows={2} placeholder="lo sentimos mucho; es culpa nuestra" className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm" />
          </label>
          <label className="block text-sm">
            Idiomas
            <input name="idiomas" defaultValue={(voice.idiomas ?? []).join("; ")} placeholder="español; inglés" className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm" />
          </label>
        </section>

        <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="font-medium">Política de auto-publicación</h2>
          <RadioOption
            name="auto_publish_policy"
            value="always_approve"
            current={business.auto_publish_policy}
            label="Aprobar todo a mano"
            help="Ningún borrador se aprueba solo; todo pasa por ti."
          />
          <RadioOption
            name="auto_publish_policy"
            value="auto_positive_only"
            current={business.auto_publish_policy}
            label="Auto solo positivas (recomendado)"
            help="Las reseñas positivas de riesgo bajo se aprueban solas; el resto espera tu OK."
          />
          <RadioOption
            name="auto_publish_policy"
            value="full_auto"
            current={business.auto_publish_policy}
            label="Auto total"
            help="Todo se aprueba solo, salvo riesgo alto."
          />
          <p className="rounded-md bg-red-50 px-3 py-2 text-xs text-red-800">
            🔒 Guardrail fijo: las reseñas de <strong>riesgo alto</strong> siempre requieren
            aprobación humana, sin importar la política. No es configurable.
          </p>
        </section>

        <button className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700">
          Guardar cambios
        </button>
      </form>
    </div>
  );
}

function RadioOption(props: { name: string; value: string; current: string; label: string; help: string }) {
  return (
    <label className="flex items-start gap-2 text-sm">
      <input
        type="radio"
        name={props.name}
        value={props.value}
        defaultChecked={props.current === props.value}
        className="mt-1"
      />
      <span>
        <span className="font-medium">{props.label}</span>
        <span className="block text-xs text-stone-500">{props.help}</span>
      </span>
    </label>
  );
}
