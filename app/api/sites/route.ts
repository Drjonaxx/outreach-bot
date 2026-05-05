import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const { userId } = auth();
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const sites = await prisma.site.findMany({
    where: { userId },
    orderBy: { createdAt: "desc" },
    select: { id: true, name: true, description: true, published: true, slug: true, createdAt: true },
  });

  return NextResponse.json({ sites });
}
