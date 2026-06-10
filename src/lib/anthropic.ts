import Anthropic from "@anthropic-ai/sdk";

/**
 * Modelo fijado por decisión de producto (ver PLAN §6).
 * Se guarda como model_version en cada output para trazabilidad.
 */
export const MODEL_VERSION = "claude-fable-5";

let client: Anthropic | null = null;

export function getAnthropic(): Anthropic {
  if (!client) {
    if (!process.env.ANTHROPIC_API_KEY) {
      throw new Error("Falta ANTHROPIC_API_KEY en el entorno");
    }
    client = new Anthropic();
  }
  return client;
}
