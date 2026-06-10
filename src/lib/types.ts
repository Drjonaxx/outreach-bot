export type Sentiment = "positivo" | "neutral" | "negativo";
export type RiskLevel = "bajo" | "medio" | "alto";
export type AutoPublishMode = "always_approve" | "auto_positive_only" | "full_auto";
export type DraftStatus = "draft" | "requires_human" | "approved" | "published" | "rejected";

export interface BrandVoice {
  tono?: string;
  valores?: string[];
  frases_prohibidas?: string[];
  frases_firma?: string[];
  idiomas?: string[];
}

export interface Business {
  id: string;
  owner_user_id: string;
  name: string;
  sector: string | null;
  brand_voice: BrandVoice;
  auto_publish_policy: AutoPublishMode;
  stripe_customer_id: string | null;
  subscription_status: string;
  created_at: string;
}

export interface Review {
  id: string;
  business_id: string;
  source: string;
  external_id: string;
  author: string | null;
  rating: number | null;
  text: string;
  review_created_at: string | null;
  raw_payload: unknown;
  created_at: string;
}

export interface Classification {
  id: string;
  review_id: string;
  sentiment: Sentiment;
  risk_level: RiskLevel;
  topics: string[];
  escalation_note: string | null;
  model_version: string;
  created_at: string;
}

export interface Draft {
  id: string;
  review_id: string;
  text: string;
  status: DraftStatus;
  model_version: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

/** Resultado de clasificación que devuelve el modelo (antes de persistir). */
export interface ClassificationResult {
  sentiment: Sentiment;
  risk_level: RiskLevel;
  topics: string[];
  escalation_note: string | null;
}

/** Reseña entrante, normalizada, independiente de la fuente. */
export interface IncomingReview {
  external_id: string;
  author: string | null;
  rating: number | null;
  text: string;
  review_created_at: string | null;
  raw_payload?: unknown;
}
