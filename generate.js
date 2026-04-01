import 'dotenv/config';
import Anthropic from '@anthropic-ai/sdk';
import { parse } from 'csv-parse/sync';
import { stringify } from 'csv-stringify/sync';
import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Config ────────────────────────────────────────────────────────────────────

const INPUT_FILE  = join(__dirname, 'businesses.csv');
const OUTPUT_CSV  = join(__dirname, 'output.csv');
const OUTPUT_MD   = join(__dirname, 'output.md');
const MODEL       = 'claude-sonnet-4-0';   // claude-sonnet-4-20250514
const DELAY_MS    = 1200;                  // pause between API calls
const MAX_RETRIES = 3;

// ── Anthropic client ──────────────────────────────────────────────────────────

if (!process.env.ANTHROPIC_API_KEY) {
  console.error('Error: ANTHROPIC_API_KEY is not set. Add it to your .env file.');
  process.exit(1);
}

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// ── Helpers ───────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function callWithRetry(fn, retries = MAX_RETRIES) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      const isRetryable =
        err instanceof Anthropic.RateLimitError ||
        err instanceof Anthropic.InternalServerError ||
        (err instanceof Anthropic.APIError && err.status >= 500);

      if (!isRetryable || attempt === retries) throw err;

      const backoff = Math.min(2 ** attempt * 1000, 30_000);
      console.warn(`  Attempt ${attempt} failed (${err.status ?? err.message}). Retrying in ${backoff / 1000}s…`);
      await sleep(backoff);
    }
  }
}

// ── Prompt ────────────────────────────────────────────────────────────────────

function buildPrompt(business) {
  const {
    name,
    niche,
    instagram_handle,
    email,
    location,
    extra_detail,
  } = business;

  const extraContext = extra_detail?.trim()
    ? `\nDetalles adicionales: ${extra_detail}`
    : '';

  return `Eres un especialista en contenido con IA y desarrollo web que ayuda a negocios locales a crecer su presencia digital.

Genera dos mensajes de contacto personalizados en ESPAÑOL para el siguiente negocio:

- Nombre: ${name}
- Nicho: ${niche}
- Instagram: ${instagram_handle}
- Email: ${email}
- Ubicación: ${location}${extraContext}

---

Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta (sin texto adicional antes o después):

{
  "dm_message": "...",
  "email_subject": "...",
  "email_body": "..."
}

Reglas para dm_message:
- Máximo 4 líneas
- Tono casual y cercano
- Sin emojis excesivos (máximo 1-2 si aplican)
- Menciona su nicho o handle de Instagram específico
- Escrito como si fueras un profesional presentándose brevemente

Reglas para el email:
- email_subject: línea de asunto atractiva y profesional, menciona su ciudad o nicho
- email_body: cuerpo del correo profesional pero cálido, 3-4 párrafos cortos
  - Menciona su ubicación (${location}) y nicho (${niche})
  - Explica brevemente cómo la IA y presencia web pueden ayudarles a crecer
  - Termina con un CTA suave: invitar a una llamada rápida o que respondan con preguntas
  - Firma como "El equipo de [Tu Agencia]" o similar`;
}

// ── Core generator ────────────────────────────────────────────────────────────

async function generateMessages(business) {
  const prompt = buildPrompt(business);

  const response = await callWithRetry(() =>
    client.messages.create({
      model: MODEL,
      max_tokens: 1024,
      messages: [{ role: 'user', content: prompt }],
    })
  );

  const rawText = response.content
    .filter(b => b.type === 'text')
    .map(b => b.text)
    .join('');

  // Extract JSON — tolerate markdown code fences
  const jsonMatch = rawText.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error(`No JSON found in response:\n${rawText}`);
  }

  const parsed = JSON.parse(jsonMatch[0]);

  if (!parsed.dm_message || !parsed.email_subject || !parsed.email_body) {
    throw new Error(`Missing fields in response: ${JSON.stringify(parsed)}`);
  }

  return {
    dm_message:    parsed.dm_message.trim(),
    email_subject: parsed.email_subject.trim(),
    email_body:    parsed.email_body.trim(),
  };
}

// ── Output formatters ─────────────────────────────────────────────────────────

function buildMarkdownSection(business, messages) {
  const { name, instagram_handle, email, location, niche } = business;
  const { dm_message, email_subject, email_body } = messages;

  return [
    `## ${name}`,
    `**Nicho:** ${niche} · **Ubicación:** ${location} · **Instagram:** ${instagram_handle} · **Email:** ${email}`,
    '',
    '### Instagram DM',
    '```',
    dm_message,
    '```',
    '',
    '### Cold Email',
    `**Asunto:** ${email_subject}`,
    '',
    email_body,
    '',
    '---',
    '',
  ].join('\n');
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  console.log('outreach-bot ▸ starting\n');

  // Read CSV
  const raw = readFileSync(INPUT_FILE, 'utf8');
  const businesses = parse(raw, { columns: true, skip_empty_lines: true, trim: true });

  if (businesses.length === 0) {
    console.error('No businesses found in businesses.csv');
    process.exit(1);
  }

  console.log(`Found ${businesses.length} business(es) to process.\n`);

  const csvRows   = [];
  const mdSections = [
    '# Outreach Messages\n',
    `Generated on ${new Date().toLocaleDateString('es-MX', { dateStyle: 'long' })}\n`,
    '---\n',
    '',
  ];

  for (let i = 0; i < businesses.length; i++) {
    const business = businesses[i];
    const label = `[${i + 1}/${businesses.length}] ${business.name}`;

    process.stdout.write(`Processing ${label}…`);

    try {
      const messages = await generateMessages(business);

      csvRows.push({
        business_name:   business.name,
        instagram_handle: business.instagram_handle,
        email:           business.email,
        dm_message:      messages.dm_message,
        email_subject:   messages.email_subject,
        email_body:      messages.email_body,
      });

      mdSections.push(buildMarkdownSection(business, messages));

      console.log(' done');
    } catch (err) {
      console.error(` FAILED — ${err.message}`);
      // Still write a row so the CSV stays aligned
      csvRows.push({
        business_name:   business.name,
        instagram_handle: business.instagram_handle,
        email:           business.email,
        dm_message:      'ERROR',
        email_subject:   'ERROR',
        email_body:      err.message,
      });
    }

    // Delay between calls (skip after last item)
    if (i < businesses.length - 1) {
      await sleep(DELAY_MS);
    }
  }

  // Write output.csv
  const csvContent = stringify(csvRows, {
    header: true,
    columns: ['business_name', 'instagram_handle', 'email', 'dm_message', 'email_subject', 'email_body'],
  });
  writeFileSync(OUTPUT_CSV, csvContent, 'utf8');

  // Write output.md
  writeFileSync(OUTPUT_MD, mdSections.join(''), 'utf8');

  console.log(`\nDone! Output saved to:`);
  console.log(`  ${OUTPUT_CSV}`);
  console.log(`  ${OUTPUT_MD}`);
}

main().catch(err => {
  console.error('\nFatal error:', err.message);
  process.exit(1);
});
