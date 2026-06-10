import type { IncomingReview } from "../types";

/**
 * Capa de lectura agnóstica de fuente (PLAN §3/§4.1).
 *
 * v1: solo ManualSource. v1.1+: GoogleBusinessProfileSource, YelpSource, etc.
 * implementan esta misma interfaz y se enchufan sin tocar el core.
 */
export interface ReviewSource {
  /** Identificador de la fuente; se persiste en reviews.source */
  readonly name: string;
  /** Normaliza la entrada cruda de la fuente a reseñas del dominio. */
  fetchReviews(input: unknown): Promise<IncomingReview[]>;
}
