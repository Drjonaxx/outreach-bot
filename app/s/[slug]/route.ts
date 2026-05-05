import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(_req: NextRequest, { params }: { params: { slug: string } }) {
  const site = await prisma.site.findUnique({ where: { slug: params.slug } });

  if (!site || !site.published) {
    return new NextResponse("Not found", { status: 404 });
  }

  return new NextResponse(site.html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
