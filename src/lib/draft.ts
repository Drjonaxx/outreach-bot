import { getAnthropic, MODEL_VERSION } from "./anthropic";
import type { BrandVoice, ClassificationResult, Review } from "./types";

/**
 * Redacta la respuesta en la voz de marca del negocio.
 * Llamada separada de la clasificación (PLAN §6): creativa, con la BrandVoice
 * inyectada en el system prompt.
 */
export async function draftReply(params: {
  review: Pick<Review, "text" | "rating" | "author">;
  classification: ClassificationResult;
  businessName: string;
  sector: string | null;
  brandVoice: BrandVoice;
}): Promise<{ text: string; modelVersion: string }> {
  const { review, classification, businessName, sector, brandVoice } = params;
  const anthropic = getAnthropic();

  const system = buildSystemPrompt(businessName, sector, brandVoice);

  const userContent = [
    `Reseña de ${review.author ?? "un cliente"} (rating: ${review.rating ?? "sin rating"}):`,
    `"""${review.text}"""`,
    ``,
    `Clasificación: sentimiento=${classification.sentiment}, riesgo=${classification.risk_level}, temas=${classification.topics.join(", ") || "ninguno"}.`,
    classification.risk_level === "alto"
      ? `IMPORTANTE: esta reseña es de RIESGO ALTO. Redacta un borrador prudente que un humano revisará antes de publicar. No respondas a las acusaciones en detalle; muestra empatía e invita a continuar el contacto en privado.`
      : `Redacta la respuesta pública lista para publicar.`,
  ].join("\n");

  const response = await anthropic.messages.create({
    model: MODEL_VERSION,
    max_tokens: 2048,
    system,
    messages: [{ role: "user", content: userContent }],
  });

  const text = response.content.find((b) => b.type === "text")?.text?.trim() ?? "";
  if (!text) throw new Error("El modelo no devolvió texto para el borrador");
  return { text, modelVersion: MODEL_VERSION };
}

function buildSystemPrompt(name: string, sector: string | null, voice: BrandVoice): string {
  const lines = [
    `Eres el community manager de "${name}"${sector ? ` (sector: ${sector})` : ""}.`,
    `Escribes respuestas públicas a reseñas de clientes en la voz de marca del negocio.`,
    ``,
    `Voz de marca:`,
    `- Tono: ${voice.tono ?? "cercano y profesional"}`,
    voice.valores?.length ? `- Valores: ${voice.valores.join(", ")}` : null,
    voice.frases_firma?.length ? `- Frases de firma (úsalas cuando encajen): ${voice.frases_firma.join(" | ")}` : null,
    voice.frases_prohibidas?.length ? `- PROHIBIDO usar: ${voice.frases_prohibidas.join(" | ")}` : null,
    voice.idiomas?.length ? `- Responde en: ${voice.idiomas.join(" o ")} (el idioma de la reseña si está en la lista)` : `- Responde en el idioma de la reseña.`,
    ``,
    `Reglas duras (no negociables):`,
    `1. Nunca admitas culpa o responsabilidad legal.`,
    `2. Nunca prometas compensación, reembolso o descuento.`,
    `3. Nunca compartas ni pidas datos privados en público.`,
    `4. En reseñas negativas, invita siempre a continuar la conversación por un canal privado.`,
    `5. Sé breve: 2 a 5 frases. Sin hashtags, sin emojis salvo que la voz de marca lo pida.`,
    ``,
    `Devuelve SOLO el texto de la respuesta, sin comillas ni explicación.`,
  ];
  return lines.filter((l): l is string => l !== null).join("\n");
}
