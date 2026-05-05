import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

async function getOwnedSite(siteId: string, userId: string) {
  const site = await prisma.site.findUnique({ where: { id: siteId } });
  if (!site || site.userId !== userId) return null;
  return site;
}

export async function GET(_req: NextRequest, { params }: { params: { siteId: string } }) {
  const { userId } = auth();
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const site = await getOwnedSite(params.siteId, userId);
  if (!site) return NextResponse.json({ error: "Not found" }, { status: 404 });

  return NextResponse.json({ site });
}

export async function PATCH(req: NextRequest, { params }: { params: { siteId: string } }) {
  const { userId } = auth();
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const site = await getOwnedSite(params.siteId, userId);
  if (!site) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const body = await req.json();
  const allowed = ["html", "name"] as const;
  const data: Partial<Record<(typeof allowed)[number], string>> = {};
  for (const key of allowed) {
    if (key in body) data[key] = body[key];
  }

  const updated = await prisma.site.update({ where: { id: params.siteId }, data });
  return NextResponse.json({ site: updated });
}

export async function DELETE(_req: NextRequest, { params }: { params: { siteId: string } }) {
  const { userId } = auth();
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const site = await getOwnedSite(params.siteId, userId);
  if (!site) return NextResponse.json({ error: "Not found" }, { status: 404 });

  await prisma.site.delete({ where: { id: params.siteId } });
  return NextResponse.json({ ok: true });
}
