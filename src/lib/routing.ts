import type { AutoPublishMode, ClassificationResult, DraftStatus } from "./types";

/**
 * Decide el destino del borrador según la política del cliente.
 *
 * GUARDRAIL (PLAN §4.4/§9): riesgo alto SIEMPRE va a humano.
 * No es configurable; ignora la política del cliente.
 */
export function decideDraftStatus(
  classification: ClassificationResult,
  policy: AutoPublishMode
): Extract<DraftStatus, "requires_human" | "approved"> {
  if (classification.risk_level === "alto") return "requires_human";

  switch (policy) {
    case "full_auto":
      return "approved";
    case "auto_positive_only":
      return classification.sentiment === "positivo" && classification.risk_level === "bajo"
        ? "approved"
        : "requires_human";
    case "always_approve":
    default:
      return "requires_human";
  }
}
