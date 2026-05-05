import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { prisma } from "@/lib/prisma";

const anthropic = new Anthropic();

const SYSTEM_PROMPT = `You are an expert web developer who creates beautiful, modern, single-page business websites.
You ONLY output valid, complete HTML with all CSS embedded in a <style> tag inside <head>.
Requirements:
- Full page: <!DOCTYPE html>, <html>, <head> (with meta charset, viewport, title), <body>
- Modern, professional design with a clear color palette and good typography
- Sections: hero, about/description, services or highlights, contact CTA
- Mobile-responsive using CSS only (no JS frameworks, no external dependencies)
- Self-contained: no external CDN links, no Google Fonts (use system fonts), no JavaScript
- Output ONLY the HTML. No explanation, no markdown fences, no preamble.`;

export async function POST(req: NextRequest) {
  const { userId } = auth();
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { name, description, style } = await req.json();
  if (!name || !description) {
    return NextResponse.json({ error: "name and description are required" }, { status: 400 });
  }

  const userPrompt = `Create a professional business website for:

Business Name: ${name}
Description: ${description}
${style ? `Visual Style: ${style}` : ""}

Output ONLY the complete HTML.`;

  // Stream from Claude and collect the full HTML
  const stream = await anthropic.messages.stream({
    model: "claude-opus-4-7",
    max_tokens: 8192,
    thinking: { type: "enabled", budget_tokens: 5000 },
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: userPrompt }],
  });

  const finalMessage = await stream.finalMessage();

  const html = finalMessage.content
    .filter((b) => b.type === "text")
    .map((b) => (b as { type: "text"; text: string }).text)
    .join("");

  if (!html.includes("<!DOCTYPE") && !html.includes("<html")) {
    return NextResponse.json({ error: "Generation failed — unexpected output" }, { status: 500 });
  }

  const site = await prisma.site.create({
    data: { userId, name, description, html },
  });

  return NextResponse.json({ siteId: site.id, slug: site.slug });
}
