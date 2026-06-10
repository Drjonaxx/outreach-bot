import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getStripe } from "@/lib/stripe";

export async function POST(request: Request) {
  const formData = await request.formData();
  const businessId = String(formData.get("business_id"));
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? new URL(request.url).origin;

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.redirect(new URL("/login", appUrl), { status: 302 });

  // RLS garantiza que solo el dueño puede leer su negocio
  const { data: business } = await supabase
    .from("businesses")
    .select("id, name, stripe_customer_id")
    .eq("id", businessId)
    .maybeSingle();
  if (!business) return new NextResponse("Negocio no encontrado", { status: 404 });

  const stripe = getStripe();

  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    customer: business.stripe_customer_id ?? undefined,
    customer_email: business.stripe_customer_id ? undefined : user.email,
    line_items: [{ price: process.env.STRIPE_PRICE_ID!, quantity: 1 }],
    metadata: { business_id: business.id },
    subscription_data: { metadata: { business_id: business.id } },
    success_url: `${appUrl}/billing?ok=1`,
    cancel_url: `${appUrl}/billing?canceled=1`,
  });

  return NextResponse.redirect(session.url!, { status: 303 });
}
