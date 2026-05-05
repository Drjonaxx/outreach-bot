import { NextRequest, NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { prisma } from "@/lib/prisma";
import Stripe from "stripe";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const sig = req.headers.get("stripe-signature");

  if (!sig) return NextResponse.json({ error: "No signature" }, { status: 400 });

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch {
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    const { siteId } = session.metadata ?? {};

    if (siteId) {
      await Promise.all([
        prisma.site.update({ where: { id: siteId }, data: { published: true } }),
        prisma.payment.updateMany({
          where: { stripeSessionId: session.id },
          data: { status: "complete" },
        }),
      ]);
    }
  }

  return NextResponse.json({ received: true });
}
