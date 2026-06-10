import { getAnthropic, MODEL_VERSION } from "./anthropic";
import type { ClassificationResult, Review, RiskLevel, Sentiment } from "./types";

const SENTIMENTS: Sentiment[] = ["positivo", "neutral", "negativo"];
const RISK_LEVELS: RiskLevel[] = ["bajo", "medio", "alto"];

const SYSTEM = `Eres un clasificador de reseñas de clientes para negocios locales.
Analizas una reseña y devuelves SOLO un objeto JSON, sin prosa ni markdown.

Criterios de risk_level:
- "alto": acusación grave (salud, seguridad, legal, fraude, discriminación), amenaza,
  mención de demanda/abogado/inspección, o cualquier contenido que exija intervención
  humana obligatoria. Ante la duda, escala a "alto".
- "medio": cliente muy molesto, reclamo de reembolso, queja repetida o reputacionalmente sensible.
- "bajo": todo lo demás.

topics: lista corta en minúsculas (ej: "servicio", "precio", "tiempo de espera",
"calidad", "staff", "limpieza", "producto").

escalation_note: solo si risk_level es "alto", una frase explicando por qué escalaste; si no, null.`;

const SCHEMA = {
  type: "object",
  properties: {
    sentiment: { type: "string", enum: SENTIMENTS },
    risk_level: { type: "string", enum: RISK_LEVELS },
    topics: { type: "array", items: { type: "string" } },
    escalation_note: { type: ["string", "null"] },
  },
  required: ["sentiment", "risk_level", "topics", "escalation_note"],
  additionalProperties: false,
} as const;

/**
 * Clasifica una reseña con Fable 5.
 * Fail-safe (PLAN §6/§9): si el parseo o la llamada fallan de forma no recuperable,
 * el llamador decide; si el JSON llega malformado, devolvemos riesgo "alto" para
 * forzar revisión humana.
 */
export async function classifyReview(
  review: Pick<Review, "text" | "rating" | "author">
): Promise<{ result: ClassificationResult; modelVersion: string }> {
  const anthropic = getAnthropic();

  const response = await anthropic.messages.create({
    model: MODEL_VERSION,
    max_tokens: 1024,
    system: SYSTEM,
    output_config: { format: { type: "json_schema", schema: SCHEMA } },
    messages: [
      {
        role: "user",
        content: JSON.stringify({
          rating: review.rating,
          author: review.author,
          texto: review.text,
        }),
      },
    ],
  });

  const text = response.content.find((b) => b.type === "text")?.text ?? "";

  try {
    const parsed = JSON.parse(text);
    return { result: normalize(parsed), modelVersion: MODEL_VERSION };
  } catch {
    // Fallback fail-safe: ante parseo fallido, tratar como riesgo alto.
    return {
      result: {
        sentiment: "neutral",
        risk_level: "alto",
        topics: [],
        escalation_note:
          "Clasificación automática falló (JSON inválido); escalada a humano por seguridad.",
      },
      modelVersion: MODEL_VERSION,
    };
  }
}

function normalize(raw: unknown): ClassificationResult {
  const obj = (raw ?? {}) as Record<string, unknown>;
  const sentiment = SENTIMENTS.includes(obj.sentiment as Sentiment)
    ? (obj.sentiment as Sentiment)
    : "neutral";
  const risk = RISK_LEVELS.includes(obj.risk_level as RiskLevel)
    ? (obj.risk_level as RiskLevel)
    : "alto"; // valor desconocido → fail-safe
  const topics = Array.isArray(obj.topics)
    ? obj.topics.filter((t): t is string => typeof t === "string").slice(0, 10)
    : [];
  const note = typeof obj.escalation_note === "string" ? obj.escalation_note : null;
  return { sentiment, risk_level: risk, topics, escalation_note: note };
}
