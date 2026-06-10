import { createClient } from "@/lib/supabase/server";
import type { Business } from "@/lib/types";

export default async function BillingPage() {
  const supabase = await createClient();
  const { data: businesses } = await supabase
    .from("businesses")
    .select("*")
    .order("created_at")
    .returns<Business[]>();

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-semibold">Facturación</h1>
      <p className="text-sm text-stone-500">
        Suscripción por negocio vía Stripe (modo test). Configura STRIPE_SECRET_KEY,
        STRIPE_PRICE_ID y el webhook para activarla.
      </p>

      <ul className="space-y-3">
        {(businesses ?? []).map((b) => (
          <li
            key={b.id}
            className="flex items-center justify-between rounded-xl border border-stone-200 bg-white p-4 shadow-sm"
          >
            <div>
              <div className="font-medium">{b.name}</div>
              <div className="text-xs text-stone-500">
                Estado:{" "}
                <span className={b.subscription_status === "active" ? "text-emerald-600" : "text-stone-500"}>
                  {b.subscription_status}
                </span>
              </div>
            </div>
            {b.subscription_status !== "active" && (
              <form action="/api/stripe/checkout" method="post">
                <input type="hidden" name="business_id" value={b.id} />
                <button className="rounded-md bg-stone-900 px-3 py-2 text-sm font-medium text-white hover:bg-stone-700">
                  Suscribirse
                </button>
              </form>
            )}
          </li>
        ))}
        {(businesses ?? []).length === 0 && (
          <li className="text-sm text-stone-500">Crea un negocio primero.</li>
        )}
      </ul>
    </div>
  );
}
