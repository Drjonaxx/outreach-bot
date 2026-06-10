import { createHash } from "crypto";
import type { IncomingReview } from "../types";
import type { ReviewSource } from "./types";

export interface ManualInput {
  /** "paste": una reseña por línea (o bloque). "csv": cabeceras author,rating,text[,date] */
  kind: "paste" | "csv";
  content: string;
}

/**
 * Fuente manual v1: el negocio pega texto o sube un CSV.
 * external_id = hash del contenido → idempotencia sin depender de IDs externos.
 */
export class ManualSource implements ReviewSource {
  readonly name = "manual";

  async fetchReviews(input: unknown): Promise<IncomingReview[]> {
    const { kind, content } = input as ManualInput;
    if (!content?.trim()) return [];
    return kind === "csv" ? parseCsv(content) : parsePaste(content);
  }
}

function contentHash(text: string, author: string | null): string {
  return createHash("sha256").update(`${author ?? ""}::${text}`).digest("hex").slice(0, 32);
}

function parsePaste(content: string): IncomingReview[] {
  // Bloques separados por líneas en blanco; si no hay, una reseña por línea.
  const blocks = content.includes("\n\n")
    ? content.split(/\n{2,}/)
    : content.split("\n");

  return blocks
    .map((b) => b.trim())
    .filter(Boolean)
    .map((text) => ({
      external_id: contentHash(text, null),
      author: null,
      rating: null,
      text,
      review_created_at: null,
      raw_payload: { kind: "paste" },
    }));
}

function parseCsv(content: string): IncomingReview[] {
  const rows = parseCsvRows(content);
  if (rows.length < 2) return [];

  const headers = rows[0].map((h) => h.trim().toLowerCase());
  const idx = {
    author: headers.indexOf("author"),
    rating: headers.indexOf("rating"),
    text: headers.indexOf("text"),
    date: headers.indexOf("date"),
  };
  if (idx.text === -1) throw new Error('El CSV necesita una columna "text"');

  return rows
    .slice(1)
    .filter((r) => r[idx.text]?.trim())
    .map((r) => {
      const text = r[idx.text].trim();
      const author = idx.author >= 0 ? r[idx.author]?.trim() || null : null;
      const ratingRaw = idx.rating >= 0 ? parseInt(r[idx.rating], 10) : NaN;
      const dateRaw = idx.date >= 0 ? r[idx.date]?.trim() : "";
      return {
        external_id: contentHash(text, author),
        author,
        rating: Number.isFinite(ratingRaw) && ratingRaw >= 1 && ratingRaw <= 5 ? ratingRaw : null,
        text,
        review_created_at: dateRaw && !isNaN(Date.parse(dateRaw)) ? new Date(dateRaw).toISOString() : null,
        raw_payload: { kind: "csv" },
      };
    });
}

/** Parser CSV mínimo con soporte de comillas dobles (RFC 4180 básico). */
function parseCsvRows(content: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < content.length; i++) {
    const ch = content[i];
    if (inQuotes) {
      if (ch === '"') {
        if (content[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && content[i + 1] === "\n") i++;
      row.push(field);
      field = "";
      if (row.some((f) => f.trim() !== "")) rows.push(row);
      row = [];
    } else {
      field += ch;
    }
  }
  row.push(field);
  if (row.some((f) => f.trim() !== "")) rows.push(row);
  return rows;
}
