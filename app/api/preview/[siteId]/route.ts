import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// Serves the raw HTML for preview inside an iframe (auth-gated, draft or published)
export async function GET(_req: NextRequest, { params }: { params: { siteId: string } }) {
  const { userId } = auth();
  if (!userId) return new NextResponse("Unauthorized", { status: 401 });

  const site = await prisma.site.findUnique({ where: { id: params.siteId } });
  if (!site || site.userId !== userId) return new NextResponse("Not found", { status: 404 });

  return new NextResponse(site.html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
