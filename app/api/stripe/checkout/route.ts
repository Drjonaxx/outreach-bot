import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { prisma } from "@/lib/prisma";

export async function POST(req: NextRequest) {
  const { userId } = auth();
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { siteId } = await req.json();
  if (!siteId) return NextResponse.json({ error: "siteId required" }, { status: 400 });

  const site = await prisma.site.findUnique({ where: { id: siteId } });
  if (!site || site.userId !== userId) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  if (site.published) {
    return NextResponse.json({ error: "Already published" }, { status: 400 });
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    line_items: [{ price: process.env.STRIPE_PRICE_ID!, quantity: 1 }],
    metadata: { siteId, userId },
    success_url: `${appUrl}/dashboard?published=${siteId}`,
    cancel_url: `${appUrl}/dashboard`,
  });

  await prisma.payment.create({
    data: { userId, siteId, stripeSessionId: session.id },
  });

  return NextResponse.json({ url: session.url });
}
