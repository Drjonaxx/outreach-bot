import { NextResponse } from "next/server";
import type Stripe from "stripe";
import { getStripe } from "@/lib/stripe";
import { createAdminClient } from "@/lib/supabase/admin";
import { logAudit } from "@/lib/audit";

/**
 * Webhook de Stripe. Usa el cliente admin (no hay sesión de usuario aquí).
 * Local: stripe listen --forward-to localhost:3000/api/stripe/webhook
 */
export async function POST(request: Request) {
  const stripe = getStripe();
  const signature = request.headers.get("stripe-signature");
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!signature || !secret) return new NextResponse("Webhook no configurado", { status: 400 });

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(await request.text(), signature, secret);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "firma inválida";
    return new NextResponse(`Webhook error: ${msg}`, { status: 400 });
  }

  const db = createAdminClient();

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object;
      const businessId = session.metadata?.business_id;
      if (businessId) {
        await db
          .from("businesses")
          .update({
            stripe_customer_id: typeof session.customer === "string" ? session.customer : null,
            subscription_status: "active",
          })
          .eq("id", businessId);
        await logAudit(db, {
          business_id: businessId,
          entity: "business",
          entity_id: businessId,
          action: "subscription_active",
          actor: "system:stripe",
        });
      }
      break;
    }
    case "customer.subscription.updated":
    case "customer.subscription.deleted": {
      const sub = event.data.object;
      const businessId = sub.metadata?.business_id;
      if (businessId) {
        const status = event.type === "customer.subscription.deleted" ? "canceled" : sub.status;
        await db.from("businesses").update({ subscription_status: status }).eq("id", businessId);
        await logAudit(db, {
          business_id: businessId,
          entity: "business",
          entity_id: businessId,
          action: `subscription_${status}`,
          actor: "system:stripe",
        });
      }
      break;
    }
  }

  return NextResponse.json({ received: true });
}
